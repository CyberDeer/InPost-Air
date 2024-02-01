import fs from 'node:fs/promises'

const manifestPath = './custom_components/inpost_air/manifest.json'
const manifest = await fs.readFile(manifestPath, 'utf-8')
const newManifest = {
    ...JSON.parse(manifest),
    version: process.argv[2]
}
fs.writeFile(manifestPath, JSON.stringify(newManifest, undefined, 2))