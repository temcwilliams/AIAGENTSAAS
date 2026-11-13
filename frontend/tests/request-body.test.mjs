import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';

// Compile the same TypeScript helper used by the route without a second implementation.
const source = readFileSync(new URL('../src/lib/request-body.ts', import.meta.url), 'utf8');
const {outputText} = ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
const {readBoundedBody, BodyTooLarge, MAX_BODY_BYTES} = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);

function request(chunks, headers = {}, onCancel = () => {}) {
  let index = 0;
  return new Request('http://localhost/api/auth/login', {
    method:'POST', headers, duplex:'half',
    body:new ReadableStream({
      pull(controller) { index < chunks.length ? controller.enqueue(chunks[index++]) : controller.close(); },
      cancel:onCancel,
    }),
  });
}

test('exact byte limit is accepted without changing bytes', async () => {
  const input = new TextEncoder().encode('x'.repeat(MAX_BODY_BYTES));
  assert.deepEqual(await readBoundedBody(request([input])), input);
});

test('multibyte chunked payload is limited by bytes and cancelled', async () => {
  let cancelled = false;
  const chunk = new TextEncoder().encode('🌱'.repeat(9000));
  await assert.rejects(readBoundedBody(request([chunk,chunk,chunk], {}, () => {cancelled=true;})), BodyTooLarge);
  assert.equal(cancelled, true);
});

test('oversized declared body is rejected before reading', async () => {
  let read = false;
  const fake = {headers:new Headers({'content-length':String(MAX_BODY_BYTES+1)}), get body(){read=true; throw new Error('must not read');}};
  await assert.rejects(readBoundedBody(fake), BodyTooLarge);
  assert.equal(read, false);
});
