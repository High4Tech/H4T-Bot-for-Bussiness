import {Area,AreaChart,CartesianGrid,XAxis,YAxis} from 'recharts';
import {ChartContainer,ChartTooltip,ChartTooltipContent,type ChartConfig} from '@/components/ui/chart';

const config={chats:{label:'Chats',color:'var(--chart-1)'}} satisfies ChartConfig;

export default function ActivityChart({bins}:{bins:{label:string;value:number}[]}){
  return <div className="activity-chart" role="img" aria-label={bins.map(b=>`${b.label}: ${b.value}`).join(', ')}>
    <ChartContainer config={config} className="h-64 w-full">
      <AreaChart accessibilityLayer data={bins} margin={{top:8,right:8,left:-26,bottom:0}}>
        <defs><linearGradient id="activity-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--color-chats)" stopOpacity={0.22}/><stop offset="95%" stopColor="var(--color-chats)" stopOpacity={0}/></linearGradient></defs>
        <CartesianGrid vertical={false} strokeDasharray="3 3"/>
        <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={10} minTickGap={26}/>
        <YAxis allowDecimals={false} tickLine={false} axisLine={false}/>
        <ChartTooltip content={<ChartTooltipContent indicator="dot"/>}/>
        <Area dataKey="value" name="chats" type="monotone" stroke="var(--color-chats)" strokeWidth={2.5} fill="url(#activity-fill)"/>
      </AreaChart>
    </ChartContainer>
  </div>;
}
