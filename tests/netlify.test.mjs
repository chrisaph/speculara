import test from 'node:test'
import assert from 'node:assert/strict'
import {backendOrigin} from '../deploy/build-netlify.mjs'

test('Netlify requires an explicit public HTTPS backend origin',()=>{
  assert.equal(backendOrigin('https://speculara-api.onrender.com/'),'https://speculara-api.onrender.com')
  for(const value of [undefined,'','http://example.com','https://localhost','https://example.com/api','https://user:pass@example.com','https://example.com/?key=secret','https://example.com/#fragment'])assert.throws(()=>backendOrigin(value))
})
