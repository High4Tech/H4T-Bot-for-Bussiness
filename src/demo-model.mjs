export const companyDefaults = {
  high4tech: {id:'high4tech',name:'High4Tech',botName:'H4T Assistant',color:'#F97328',welcome:"Hi there! How can we help you today?",description:'A little help, right when you need it.',avatar:'/assets/brand/mascots.svg',logo:'/assets/brand/wordmark.png',questions:['Explore services','How does this demo work?','Talk to a person'],leadForm:false,position:'right',dark:false},
  cedar: {id:'cedar',name:'Cedar Studio',botName:'Cedar Guide',color:'#28745B',welcome:"Welcome to Cedar. What can we help you with?",description:'Let’s make something thoughtful.',avatar:'/assets/brand/favicon.png',logo:'',questions:['Explore the studio','How does this demo work?','Talk to a person'],leadForm:false,position:'left',dark:false}
};
export function demoReply(text) {
  if (/person|human|agent|handoff/i.test(text)) return {text:'Demo: your request is now in the local inbox. No real agent has been notified.',handoff:true};
  if (/^(hi|hello|hey|thanks|thank you)[! .]*$/i.test(text.trim())) return {text:'Hello! You’re trying a local interface demo. What would you like to explore?',handoff:false};
  if (/demo|work/i.test(text)) return {text:'This sample chat uses scripted replies. Create a business and publish knowledge to try the local AI assistant, or request a person to preview handoff.',handoff:false};
  return {text:'This sample has no published business knowledge, so I can’t verify that answer. Create a business to try knowledge-backed replies, or request a person.',handoff:false};
}
export function platformProjection(companies) {
  return companies.map(({id,name,plan,status,bots,answers,storage})=>({id,name,plan,status,bots,answers,storage}));
}
export function allowedTransition(from,to) {
  return ({BOT_ACTIVE:['HUMAN_REQUESTED','HUMAN_ASSIGNED','RESOLVED'],HUMAN_REQUESTED:['HUMAN_ASSIGNED','RESOLVED'],HUMAN_ASSIGNED:['BOT_ACTIVE','RESOLVED'],RESOLVED:['BOT_ACTIVE']})[from]?.includes(to) ?? false;
}
export function mergeDemoConversations(local,incoming) {
  const localIds=new Set(local.map(c=>c.id));
  return [...local,...incoming.filter(c=>!localIds.has(c.id))];
}
