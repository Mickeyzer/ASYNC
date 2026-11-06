// Recover locally cached public npm archives without modifying the global cache.
// Normal machines can use `npm ci` instead. This helper makes no network requests.
const fs = require('node:fs/promises');
const path = require('node:path');
const zlib = require('node:zlib');
const npmModules = path.join(path.dirname(process.execPath), 'node_modules/npm/node_modules');
const cacache = require(path.join(npmModules, 'cacache'));
const semver = require(path.join(npmModules, 'semver'));
const root = path.resolve(__dirname, '..');
const destination = path.join(root, '.npm-cache/_cacache');
const source = path.join(process.env.LOCALAPPDATA, 'npm-cache/_cacache');
const prefix = 'make-fetch-happen:request-cache:';

function readManifest(archive, expectedName) {
  const tar = zlib.gunzipSync(archive);
  for (let offset = 0; offset + 512 <= tar.length;) {
    const header = tar.subarray(offset, offset + 512);
    const name = header.subarray(0, 100).toString().replace(/\0.*$/, '');
    const size = parseInt(header.subarray(124, 136).toString().replace(/\0.*$/, '').trim(), 8) || 0;
    if (!name) break;
    const start = offset + 512;
    if (/^[^/]+\/package\.json$/.test(name)) {
      const manifest = JSON.parse(tar.subarray(start, start + size).toString());
      if (manifest.name === expectedName) return manifest;
    }
    offset = start + Math.ceil(size / 512) * 512;
  }
  throw new Error(`No matching package manifest in cached archive: ${expectedName}`);
}

function metadata(url, type) {
  return {time: Date.now(), url, reqHeaders: {accept: type === 'application/json' ? 'application/json' : '*/*'}, resHeaders: {'content-type': type, 'cache-control': 'public, max-age=31536000', date: new Date().toUTCString()}, options: {compress: true}};
}

async function main() {
  const entries = Object.values(await cacache.ls(source));
  const index = new Map();
  for (const entry of entries) {
    if (!entry.key.startsWith(prefix + 'https://registry.npmjs.org/') || !entry.key.endsWith('.tgz')) continue;
    const url = entry.key.slice(prefix.length);
    const name = new URL(url).pathname.split('/-/')[0].slice(1);
    const archiveName = url.split('/-/')[1];
    const basename = name.split('/').at(-1);
    const version = archiveName.slice(basename.length + 1, -4);
    if (!semver.valid(version)) continue;
    if (!index.has(name)) index.set(name, []);
    index.get(name).push({entry, version, url});
  }
  const project = JSON.parse(await fs.readFile(path.join(root, 'frontend/package.json'), 'utf8'));
  const queue = Object.entries({...project.dependencies, ...project.devDependencies}).map(([name, range]) => ({name, range, required: true}));
  const restored = new Map();
  const skipped = new Set();
  while (queue.length) {
    const {name, range, required} = queue.shift();
    const candidates = (index.get(name) || []).filter(item => semver.satisfies(item.version, range)).sort((a,b) => semver.rcompare(a.version,b.version));
    if (!candidates.length) {
      if (required) throw new Error(`Required dependency absent from local cache: ${name}@${range}`);
      skipped.add(name);
      continue;
    }
    const candidate = candidates[0];
    const identity = `${name}@${candidate.version}`;
    if (restored.has(identity)) continue;
    const cached = await cacache.get(source, candidate.entry.key);
    const manifest = readManifest(cached.data, name);
    const supports = (list, value) => !list || (!list.includes('!' + value) && (!list.some(item => !item.startsWith('!')) || list.includes(value)));
    if (!supports(manifest.os, process.platform) || !supports(manifest.cpu, process.arch)) {
      if (required) throw new Error(`Unsupported required package platform: ${identity}`);
      skipped.add(name);
      continue;
    }
    const integrity = await cacache.put(destination, candidate.entry.key, cached.data, {metadata: metadata(candidate.url, 'application/octet-stream')});
    manifest.dist = {tarball: candidate.url, integrity: String(integrity)};
    restored.set(identity, manifest);
    for (const [dependency, constraint] of Object.entries(manifest.dependencies || {})) queue.push({name: dependency, range: constraint, required});
    for (const [dependency, constraint] of Object.entries(manifest.optionalDependencies || {})) queue.push({name: dependency, range: constraint, required: false});
  }
  const packuments = new Map();
  for (const manifest of restored.values()) {
    if (!packuments.has(manifest.name)) packuments.set(manifest.name, {name: manifest.name, versions: {}, 'dist-tags': {latest: manifest.version}});
    packuments.get(manifest.name).versions[manifest.version] = manifest;
  }
  for (const [name, packument] of packuments) {
    const url = 'https://registry.npmjs.org/' + name.replace('/', '%2f');
    await cacache.put(destination, prefix + url, JSON.stringify(packument), {metadata: metadata(url, 'application/json')});
  }
  console.log(`Restored ${restored.size} package archives and ${packuments.size} metadata records into the project cache.`);
  console.log(`Optional archives unavailable locally: ${skipped.size}. npm will select the supported local platform.`);
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
