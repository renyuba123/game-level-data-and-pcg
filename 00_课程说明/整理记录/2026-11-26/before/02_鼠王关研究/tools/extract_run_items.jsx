(function(){
 var root=File($.fileName).parent.parent, files=['outputs/ratking_run-001/ratking_run-001_edited.ai','002.ai','003_.ai','004.ai','005_.ai'];
 var out=File(root.fsName+'/outputs/native_runs_001_005.tsv');out.encoding='UTF-8';out.open('w');out.writeln('run\ttype\tlayer\tuuid\tx1\ty1\tx2\ty2');
 function child(l,n){for(var i=0;i<l.layers.length;i++)if(l.layers[i].name===n)return l.layers[i];return null;}
 function top(d,n){for(var i=0;i<d.layers.length;i++)if(d.layers[i].name===n)return d.layers[i];return null;}
 function cen(p){var b=p.geometricBounds;return [(b[0]+b[2])/2,(b[1]+b[3])/2+1500];}
 for(var r=0;r<files.length;r++){
  var doc=app.open(File(root.fsName+'/'+files[r]));var org=top(doc,'original'),route=org&&child(org,'Route');
  if(!route)throw Error('Missing original/Route in '+files[r]);
  for(var j=0;j<route.pathItems.length;j++){var p=route.pathItems[j],a=p.pathPoints[0].anchor,b=p.pathPoints[p.pathPoints.length-1].anchor;out.writeln((r+1)+'\troute\tRoute\t'+p.uuid+'\t'+a[0]+'\t'+(a[1]+1500)+'\t'+b[0]+'\t'+(b[1]+1500));}
  var ev=top(doc,'F-Event-Labels'),icons=ev&&child(ev,'ori_events');if(!icons)throw Error('Missing ori_events');
  for(var k=0;k<icons.layers.length;k++)for(var j=0;j<icons.layers[k].pathItems.length;j++){var p=icons.layers[k].pathItems[j],c=cen(p);out.writeln((r+1)+'\tevent\t'+icons.layers[k].name+'\t'+p.uuid+'\t'+c[0]+'\t'+c[1]+'\t\t');}
  doc.close(SaveOptions.DONOTSAVECHANGES);
 }
 out.close();
})();
