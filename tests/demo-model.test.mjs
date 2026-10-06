import test from 'node:test';
import assert from 'node:assert/strict';
import {demoReply,allowedTransition,platformProjection,companyDefaults,mergeDemoConversations} from '../src/demo-model.mjs';
test('unsupported company facts cannot become fabricated demo answers',()=>{const result=demoReply('What is your refund policy and price?');assert.match(result.text,/no published business knowledge/);assert.equal(result.handoff,false);});
test('human escalation is explicit and never claims a real notification',()=>{const result=demoReply('I need a human agent');assert.equal(result.handoff,true);assert.match(result.text,/No real agent has been notified/);});
test('claim, resume and resolve obey the demo state lifecycle',()=>{assert.equal(allowedTransition('HUMAN_REQUESTED','HUMAN_ASSIGNED'),true);assert.equal(allowedTransition('HUMAN_ASSIGNED','BOT_ACTIVE'),true);assert.equal(allowedTransition('RESOLVED','HUMAN_ASSIGNED'),false);assert.equal(allowedTransition('BOT_ACTIVE','BOGUS'),false);});
test('platform metadata projection drops private customer fields',()=>{const [projected]=platformProjection([{id:'a',name:'A',plan:'Demo',status:'active',bots:1,answers:0,storage:'0',conversations:['private'],visitors:['private'],documents:['private'],secret:'secret'}]);assert.deepEqual(Object.keys(projected),['id','name','plan','status','bots','answers','storage']);});
test('two company configurations have independent themes',()=>{assert.notEqual(companyDefaults.high4tech.color,companyDefaults.cedar.color);assert.notEqual(companyDefaults.high4tech.name,companyDefaults.cedar.name);});
test('late preview-tab synchronization preserves a newly started chat and its replies',()=>{
 const local=[{id:'new-chat',messages:['Hello']},{id:'sample',messages:['Current reply']}];
 const stale=[{id:'sample',messages:[]},{id:'remote-chat',messages:['Remote']}];
 assert.deepEqual(mergeDemoConversations(local,stale),[...local,stale[1]]);
});
