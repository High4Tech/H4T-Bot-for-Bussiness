export interface BotConfig {id:string;name:string;botName:string;color:string;welcome:string;description:string;avatar:string;logo:string;questions:string[];leadForm:boolean;position:string;dark:boolean}
export const companyDefaults: Record<string, BotConfig>;
export function demoReply(text:string):{text:string;handoff:boolean};
export function allowedTransition(from:string,to:string):boolean;
export function platformProjection(companies: Record<string,unknown>[]): Record<string,unknown>[];
export function mergeDemoConversations<T extends {id:string}>(local:T[],incoming:T[]):T[];
