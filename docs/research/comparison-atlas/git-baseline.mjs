// Experimento local con datos sintéticos. No configura ni simula ACL de GitHub.
// No usa cuentas, red, hooks, configuración global de Git ni credenciales.
// Conserva cada ejecución en un directorio nuevo para inspección posterior.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';

const here = path.dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(fs.readFileSync(path.join(here, 'case-atlas.json'), 'utf8'));
const parent = path.resolve(process.argv[2] ?? os.tmpdir());
fs.mkdirSync(parent, { recursive: true });
const run = fs.mkdtempSync(path.join(parent, 'atlas-git-'));
const repo = path.join(run, 'atlas-shared');
const privateDir = path.join(run, 'ana-private');
fs.mkdirSync(repo);
fs.mkdirSync(privateDir);
fs.writeFileSync(path.join(privateDir, 'source.txt'), fixture.source.text);
const env = {
  PATH: process.env.PATH,
  LANG: 'C',
  GIT_CONFIG_NOSYSTEM: '1',
  GIT_CONFIG_GLOBAL: '/dev/null',
  GIT_TERMINAL_PROMPT: '0',
  GIT_AUTHOR_NAME: 'Synthetic Test Actor',
  GIT_AUTHOR_EMAIL: 'test@example.invalid',
  GIT_COMMITTER_NAME: 'Synthetic Test Actor',
  GIT_COMMITTER_EMAIL: 'test@example.invalid',
};
const commands = [];
function git(cwd, ...args) {
  const full = ['-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', ...args];
  const output = execFileSync('git', full, { cwd, env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  commands.push({ cwd: path.relative(run, cwd), args, stdout: output.trim() });
  return output.trim();
}
const results = [];
function check(id, description, test, observation) {
  test();
  results.push({ id, assertion: 'passed', description, observation });
}
git(repo, 'init', '-b', 'main');
git(repo, 'commit', '--allow-empty', '-m', 'Synthetic baseline');
git(repo, 'switch', '-c', 'candidate');
fs.writeFileSync(path.join(repo, 'lesson.md'), fixture.candidate_v1.text);
git(repo, 'add', 'lesson.md');
git(repo, 'commit', '-m', 'Candidate v1; NOT a GitHub approval');
const v1 = git(repo, 'rev-parse', 'HEAD');
const readClone = path.join(run, 'reader-before-approval');
git(run, 'clone', '--no-local', '--branch', 'main', repo, readClone);
check('G1', 'La rama main aún no tiene la lección', () => {
  assert.equal(fs.existsSync(path.join(readClone, 'lesson.md')), false);
}, 'Filtrar por main evita usar el borrador en el consumo normal.');
check('G2', 'El clon del mismo repo puede leer la rama candidata', () => {
  assert.match(git(readClone, 'show', 'origin/candidate:lesson.md'), /event_id/);
}, 'Main-only no es confidencialidad de borradores: la rama candidata también se recibió.');
check('G3', 'Los marcadores privados no están en los blobs compartidos', () => {
  const listing = git(repo, 'rev-list', '--objects', '--all');
  const objectText = listing.split('\n').filter(Boolean).map(line => git(repo, 'cat-file', '-p', line.split(' ')[0])).join('\n');
  for (const marker of fixture.forbidden_markers) assert.equal(objectText.includes(marker), false);
}, 'La separación se consiguió preparando manualmente el candidato, no por anonimización de Git.');
fs.writeFileSync(path.join(repo, 'lesson.md'), fixture.candidate_v2.text);
git(repo, 'add', 'lesson.md');
git(repo, 'commit', '-m', 'Edit candidate after hypothetical review');
const v2 = git(repo, 'rev-parse', 'HEAD');
check('G4', 'Editar cambia el commit y conserva la versión anterior', () => {
  assert.notEqual(v1, v2);
  assert.match(git(repo, 'show', `${v1}:lesson.md`), /5 reintentos/);
  assert.match(git(repo, 'show', `${v2}:lesson.md`), /3 reintentos/);
}, 'Identidad de versión comprobada; invalidación de una aprobación GitHub NO ejecutada.');
git(repo, 'switch', 'main');
git(repo, 'merge', '--ff-only', v1);
const bruno = path.join(run, 'bruno-after-publication');
git(run, 'clone', '--no-local', '--branch', 'main', repo, bruno);
check('G5', 'Otro checkout recupera la lección publicada por búsqueda lexical', () => {
  assert.match(git(bruno, 'grep', '-n', 'event_id', 'HEAD', '--', 'lesson.md'), /event_id/);
}, 'Consulta Git real, no dos humanos autenticados ni un harness/LLM en ejecución.');
fs.writeFileSync(path.join(repo, 'skill.md'), fixture.derived_skill_v1.text);
git(repo, 'add', 'skill.md');
git(repo, 'commit', '-m', 'Create derived skill without dependency automation');
fs.writeFileSync(path.join(repo, 'lesson.md'), fixture.candidate_v2.text);
git(repo, 'add', 'lesson.md');
git(repo, 'commit', '-m', 'Correct source to v2');
check('G6', 'Una corrección no actualiza automáticamente la skill derivada', () => {
  assert.match(fs.readFileSync(path.join(repo, 'lesson.md'), 'utf8'), /3 reintentos/);
  assert.match(fs.readFileSync(path.join(repo, 'skill.md'), 'utf8'), /5 reintentos/);
}, 'Git no interpreta esa dependencia semántica en este baseline.');
git(repo, 'rm', 'lesson.md');
git(repo, 'commit', '-m', 'Withdraw lesson from current tree');
check('G7', 'Retirar de main no elimina historia ni copias previas', () => {
  assert.equal(fs.existsSync(path.join(repo, 'lesson.md')), false);
  assert.match(git(repo, 'show', `${v1}:lesson.md`), /event_id/);
  assert.match(fs.readFileSync(path.join(bruno, 'lesson.md'), 'utf8'), /5 reintentos/);
}, 'El borrado actual no es revocación de contenido ya distribuido.');
const releasedRepo = path.join(run, 'atlas-approved-only');
fs.mkdirSync(releasedRepo);
git(releasedRepo, 'init', '-b', 'main');
fs.writeFileSync(path.join(releasedRepo, 'lesson.md'), fixture.candidate_v1.text);
git(releasedRepo, 'add', 'lesson.md');
git(releasedRepo, 'commit', '-m', 'Publish sanitized snapshot without review-branch history');
const releasedClone = path.join(run, 'reader-approved-only');
git(run, 'clone', '--no-local', releasedRepo, releasedClone);
check('G8', 'Un repositorio de distribución separado no incluye la rama candidata', () => {
  const branches = git(releasedClone, 'branch', '-a');
  const commits = git(releasedClone, 'rev-list', '--all');
  assert.equal(branches.includes('candidate'), false);
  assert.equal(commits.includes(v2), false);
  assert.match(fs.readFileSync(path.join(releasedClone, 'lesson.md'), 'utf8'), /5 reintentos/);
}, 'Alternativa fuerte: revisión restringida y distribución en repositorios distintos. Se comprobó separación de contenido, NO ACL ni aprobación real.');
const report = {
  case_id: fixture.case_id,
  executed_at: new Date().toISOString(),
  git_version: git(repo, '--version'),
  node_version: process.version,
  run_directory: run,
  versions: { v1, v2 },
  disclaimer: '8 aserciones sobre Git local; no son 8 requisitos de producto satisfechos. Sin servidor, PR real, ACL, revisión humana ni extracción automática.',
  results,
  commands,
};
fs.writeFileSync(path.join(run, 'results.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
