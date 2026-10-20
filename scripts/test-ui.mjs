import {readdirSync,existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
const fixture=process.env.WAR_HAVEN_DASHBOARD_FIXTURE;
if(!fixture||!existsSync(fixture))throw Error('Generate tests/fixtures/leadership.html and set WAR_HAVEN_DASHBOARD_FIXTURE.');
const files=readdirSync('tests').filter(file=>file.endsWith('.test.mjs')).sort();
if(!files.length)throw Error('No UI acceptance tests found.');
for(const file of files){
 const result=spawnSync(process.execPath,['tests/'+file],{stdio:'inherit',env:process.env});
 if(result.status!==0)process.exit(result.status||1);
}
console.log('All '+files.length+' dashboard UI suites passed.');
