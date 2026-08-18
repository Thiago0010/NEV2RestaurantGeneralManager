import test from 'node:test';
import assert from 'node:assert/strict';
import { extractErrorMessage } from './error.js';

test('extractErrorMessage handles plain strings and nested API errors', () => {
  assert.equal(extractErrorMessage('bad request'), 'bad request');
  assert.equal(extractErrorMessage({ detail: 'Slug already in use' }), 'Slug already in use');
  assert.equal(extractErrorMessage({ message: { detail: 'Email already registered' } }), 'Email already registered');
  assert.equal(extractErrorMessage({}), 'Erro ao processar a solicitação.');
});
