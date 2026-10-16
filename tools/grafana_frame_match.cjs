// Match a capture's identity and UTC, rather than a newer unrelated row.
function containsCapture(response,capture){
  for(const result of Object.values(response.results||{}))for(const frame of result.frames||[]){
    const fields=frame.schema?.fields||[],values=frame.data?.values||[];
    const id=fields.findIndex(f=>f.name==='sample_id'),time=fields.findIndex(f=>f.type==='time');
    if(id<0||time<0)continue;
    for(let i=0;i<(values[id]||[]).length;++i)
      if(values[id][i]===capture.sample_id && values[time]?.[i]===capture.timestamp*1000)return true;
  }
  return false;
}
module.exports={containsCapture};
