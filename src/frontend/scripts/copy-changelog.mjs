import { copyFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = fileURLToPath(new URL('.', import.meta.url));
const sourcePath = resolve(scriptDir, '../../../CHANGELOG.md');
const destinationPath = resolve(scriptDir, '../CHANGELOG.md');

try {
	await copyFile(sourcePath, destinationPath);
	console.log('Copied CHANGELOG.md into frontend workspace.');
} catch (error) {
	console.error(`Failed to copy CHANGELOG.md: ${error}`);
	process.exit(1);
}
