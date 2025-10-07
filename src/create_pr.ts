import { Octokit } from '@octokit/rest';
import * as dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';

// Load .env file if present
dotenv.config();

// Basic contract: read env vars or fall back to defaults
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const OWNER = process.env.OWNER ?? 'Klerno-Labs';
const REPO = process.env.REPO ?? 'Klerno-Labs';
const HEAD = process.env.HEAD_BRANCH ?? 'chore/typing-sweep';
const BASE = process.env.BASE_BRANCH ?? 'main';
const TITLE = process.env.PR_TITLE ?? 'chore(typing): conservative DB typing sweep + permissive Protocol shim';
const PR_BODY_FILE = process.env.PR_BODY_FILE ?? 'PR_BODY_typing_sweep.md';
const REVIEWERS = (process.env.REVIEWERS ?? '').split(',').filter(Boolean);

if (!GITHUB_TOKEN) {
    console.error('GITHUB_TOKEN not set - create a short-lived token and set GITHUB_TOKEN in .env or env vars');
    process.exit(1);
}

const octokit = new Octokit({ auth: GITHUB_TOKEN });

async function main() {
    try {
        const bodyPath = path.resolve(process.cwd(), PR_BODY_FILE);
        const body = fs.existsSync(bodyPath) ? fs.readFileSync(bodyPath, 'utf8') : '';

        console.log(`Creating PR ${OWNER}/${REPO}: ${TITLE}`);

        const { data: pr } = await octokit.pulls.create({
            owner: OWNER,
            repo: REPO,
            title: TITLE,
            head: HEAD,
            base: BASE,
            body,
        });

        console.log(`PR created: ${pr.html_url}`);

        if (REVIEWERS.length > 0) {
            console.log(`Requesting reviewers: ${REVIEWERS.join(',')}`);
            await octokit.pulls.requestReviewers({
                owner: OWNER,
                repo: REPO,
                pull_number: pr.number,
                reviewers: REVIEWERS,
            });
            console.log('Reviewers requested');
        }

        console.log('Done');
    } catch (err) {
        console.error('Error creating PR:', err);
        process.exit(1);
    }
}

main();
