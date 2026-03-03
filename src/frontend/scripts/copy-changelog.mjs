import { copyFile, access, constants } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = fileURLToPath(new URL('.', import.meta.url));
const destinationPath = resolve(scriptDir, '../CHANGELOG.md');
const sourceCandidates = [
	resolve(scriptDir, '../../../CHANGELOG.md'),
	resolve(scriptDir, '../CHANGELOG.md')
];

try {
	let sourcePath = null;
	for (const candidatePath of sourceCandidates) {
		try {
			await access(candidatePath, constants.F_OK);
			sourcePath = candidatePath;
			break;
		} catch {
			// continue searching
		}
	}

	if (sourcePath === null) {
		console.warn('CHANGELOG.md not found in expected locations. Skipping copy.');
		process.exit(0);
	}

	await copyFile(sourcePath, destinationPath);
	console.log(`Copied CHANGELOG.md from ${sourcePath} to frontend workspace.`);
} catch (error) {
	console.error(`Failed to copy CHANGELOG.md: ${error}`);
	process.exit(1);
}
