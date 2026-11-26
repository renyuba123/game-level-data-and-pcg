/* Update five saved Illustrator documents from source/depthmap/shuwang.graph and the DXF. */
(function(){
 var map=/*MAP_LITERAL*/null,runs=/*RUNS_LITERAL*/null;
 var root=File($.fileName).parent.parent;
 function rgb(s){var c=new RGBColor();c.red=parseInt(s.substr(1,2),16);c.green=parseInt(s.substr(3,2),16);c.blue=parseInt(s.substr(5,2),16);return c;}
 function top(d,n){for(var i=0;i<d.layers.length;i++)if(d.layers[i].name===n)return d.layers[i];return null;}
 function child(l,n){for(var i=0;i<l.layers.length;i++)if(l.layers[i].name===n)return l.layers[i];return null;}
 function layer(d,n){var l=top(d,n);if(l){l.locked=false;l.visible=true;l.remove();}l=d.layers.add();l.name=n;return l;}
 function text(l,s,x,y,size,color){var t=l.textFrames.add();t.contents=s;t.position=[x,y-1500];t.textRange.characterAttributes.size=size;t.textRange.characterAttributes.fillColor=rgb(color||'#203044');return t;}
 function path(l,pts,fill,stroke,sw){var p=l.pathItems.add();p.setEntirePath(pts);p.closed=!!fill;p.filled=!!fill;if(fill)p.fillColor=rgb(fill);p.stroked=!!stroke;if(stroke){p.strokeColor=rgb(stroke);p.strokeWidth=sw||1;}return p;}
 function rect(l,x,y,w,h,color){return path(l,[[x,y-1500],[x+w,y-1500],[x+w,y-h-1500],[x,y-h-1500]],color,null,0);}
 function line(l,a,b,color,sw){return path(l,[[a[0],a[1]-1500],[b[0],b[1]-1500]],null,color,sw);}
 function circle(l,x,y,r,fill){var p=l.pathItems.ellipse(y+r-1500,x-r,2*r,2*r);p.filled=true;p.fillColor=rgb(fill);p.stroked=false;return p;}
 function heading(l,n,title,subtitle){text(l,n+'  '+title,50,1224,27,'#172B44');text(l,subtitle,52,1194,14,'#4E5B6A');line(l,[1495,285],[1495,1180],'#D3D9E0',1.2);}
 function num(v){if(Math.abs(v)>=1000)return Math.round(v).toLocaleString('en-US');return String(Math.round(v*100)/100);}
 function band(v,p){var t=(v-p.min)/(p.max-p.min);return Math.max(0,Math.min(9,Math.floor(t*10)));}
 function pointMap(d,name,numTitle,title,colIndex,palette){var l=layer(d,name),cells=l.layers.add();cells.name=name.replace('-Labels','');for(var i=0;i<map.vga.length;i++){var p=map.vga[i],c=palette.colors[band(p[colIndex],palette)];rect(cells,p[0]-5.3,p[1]+5.3,10.6,10.6,c);}heading(l,numTitle,title,runs[runIndex].run_id+' / source/depthmap/shuwang.graph / 3,468 VGA points');text(l,title==='METRIC MEAN SHORTEST-PATH DISTANCE'?'METRIC DISTANCE':title,1525,1150,21);text(l,'Range '+num(palette.min)+' - '+num(palette.max),1525,1104,15);text(l,'10 equal value intervals',1525,1068,15,'#167647');for(var k=0;k<10;k++){var y=1023-k*58;rect(l,1525,y+11,24,24,palette.colors[k]);text(l,num(palette.bounds[k])+' - '+num(palette.bounds[k+1]),1563,y+3,13);}text(l,'Derived vector palette',1525,420,14);text(l,'Graph units; scale unverified',1525,387,14);if(title==='GATE COUNTS')text(l,'Not player traversal count',1525,350,14,'#9A5A16');return l;}
 function view(d,names){for(var i=0;i<d.layers.length;i++)d.layers[i].visible=false;for(var j=0;j<names.length;j++){var l=top(d,names[j]);if(!l)throw Error('Missing '+names[j]);l.visible=true;}}
 function exportView(d,out,name,names){view(d,names);var svg=new ExportOptionsSVG();svg.embedRasterImages=true;svg.coordinatePrecision=3;svg.fontSubsetting=SVGFontSubsetting.GLYPHSUSED;svg.fontType=SVGFontType.OUTLINEFONT;d.exportFile(File(out.fsName+'/'+name+'.svg'),ExportType.SVG,svg);var png=new ExportOptionsPNG24();png.antiAliasing=true;png.transparency=false;png.artBoardClipping=true;png.horizontalScale=100;png.verticalScale=100;d.exportFile(File(out.fsName+'/'+name+'.png'),ExportType.PNG24,png);}
 for(var runIndex=0;runIndex<runs.length;runIndex++){
  var run=runs[runIndex],id=run.run_id;
  var out=Folder(root.fsName+'/outputs/'+id);if(!out.exists)out.create();
  var log=File(out.fsName+'/shuwang_render.log');log.encoding='UTF-8';log.open('w');log.writeln('SOURCE '+run.source_ai+' GRAPH '+map.graph_sha256+' DXF '+map.dxf_sha256);
  var src=(runIndex===0)?File(out.fsName+'/'+id+'_edited.ai'):File(root.fsName+'/'+run.source_ai);
  if(!src.exists)throw Error('Missing source '+src.fsName);
  var doc=app.open(src),original=top(doc,'original'),ev=top(doc,'F-Event-Labels');
  if(!original||!ev)throw Error('Missing original or event layer in '+src.fsName);
  var icons=child(ev,'ori_events');if(!icons)throw Error('Missing original event icons '+id);
  // Replace building paths with the current DXF, using the registered graph XY -> AI transform.
  var walls=layer(doc,'F-Walls');for(var i=0;i<map.walls.length;i++){var w=map.walls[i],ink=w[0]==='wall'?'#555D64':w[0]==='through'?'#8A9EA8':'#A3AAB0';line(walls,[w[1],w[2]],[w[3],w[4]],ink,w[0]==='wall'?1.2:0.8);}
  var cadDetails=walls.layers.add();cadDetails.name='F-CAD-Details';
  for(var i=0;i<map.circles.length;i++){var circlePts=[];for(var j=0;j<map.circles[i][1].length;j++)circlePts.push([map.circles[i][1][j][0],map.circles[i][1][j][1]-1500]);var circlePath=path(cadDetails,circlePts,null,'#D9AB00',1.8);circlePath.closed=true;}
  for(var i=0;i<map.polylines.length;i++){var polyPts=[];for(var j=0;j<map.polylines[i][1].length;j++)polyPts.push([map.polylines[i][1][j][0],map.polylines[i][1][j][1]-1500]);var polyPath=path(cadDetails,polyPts,null,'#555D64',1.2);polyPath.closed=map.polylines[i][2];}
  var choice=layer(doc,'F-Choice-Labels'),regions=choice.layers.add();regions.name='F-ConvexChoice';heading(choice,'03','CONVEX CHOICE',id+' / source/depthmap/shuwang.graph / 11 regions');
  var choiceColors=['#E7F1FB','#B6DBEC','#88C6DE','#56AACB','#E7D75A','#E89656','#D94828'];
  for(var i=0;i<map.convex.length;i++){var c=map.convex[i],v=c[2],ci=Math.min(6,Math.floor(v/63*7)),pts=[];for(var j=0;j<c[4].length;j++)pts.push([c[4][j][0],c[4][j][1]-1500]);var p=path(regions,pts,choiceColors[ci],null,0);p.opacity=75;var sx=0,sy=0;for(var j=0;j<c[4].length;j++){sx+=c[4][j][0];sy+=c[4][j][1];}text(choice,c[0]+'  '+num(v),sx/c[4].length,sy/c[4].length,15);}
  text(choice,'Choice / 0 - 62',1525,1150,22);text(choice,'11 Convex Map regions',1525,1104,16);text(choice,'R01-R11 / exported values',1525,1068,15);
  for(var k=0;k<7;k++){var cy=1017-k*58;rect(choice,1525,cy+11,24,24,choiceColors[k]);text(choice,(k*9)+' - '+Math.min(62,k*9+8),1563,cy+3,14);}
  text(choice,'Physical scale unverified',1525,564,15);
  pointMap(doc,'F-VGA-Labels','04','VISUAL INTEGRATION [HH]',2,map.palettes['Visual Integration [HH]']);
  pointMap(doc,'F-Gate-Counts-Labels','05','GATE COUNTS',3,map.palettes['Gate Counts']);
  pointMap(doc,'F-Metric-Labels','06','METRIC MEAN SHORTEST-PATH DISTANCE',4,map.palettes['Metric Mean Shortest-Path Distance']);
  var movement=layer(doc,'F-Movement-Labels'),route=movement.layers.add();route.name='F-Movement-Route';heading(movement,'01','PLAYER ROUTE',id+' / geometric candidate order');
  for(var i=0;i<run.segments.length;i++){var s=run.segments[i];line(route,s.a,s.b,'#186BB8',3.2);if(i%3===0){var mx=(s.a[0]+s.b[0])/2,my=(s.a[1]+s.b[1])/2,dx=s.b[0]-s.a[0],dy=s.b[1]-s.a[1],len=Math.sqrt(dx*dx+dy*dy)||1,ux=dx/len,uy=dy/len;path(route,[[mx+ux*8,my+uy*8-1500],[mx-ux*7-uy*5,my-uy*7+ux*5-1500],[mx-ux*7+uy*5,my-uy*7-ux*5-1500]],'#186BB8',null,0);}}
  var spawn=run.events[0].xy;circle(movement,spawn[0],spawn[1],9,'#20A65A');circle(movement,run.end[0],run.end[1],9,'#7446A7');text(movement,'Spawn',spawn[0]+12,spawn[1]+10,16,'#167647');text(movement,'End',run.end[0]+13,run.end[1]+8,16,'#7446A7');text(movement,'Drawn route / '+run.segments.length+' segments',1525,1150,18);text(movement,'Start: green Spawn',1525,1106,16,'#167647');text(movement,'End: purple marker',1525,1071,16,'#7446A7');text(movement,'Local order is candidate',1525,1015,15,'#9A5A16');text(movement,'No verified timestamps',1525,984,15,'#9A5A16');
  // Keep all original event paths, removing only stale labels and the old pale 001 route.
  ev.locked=false;ev.visible=true;for(var k=ev.layers.length-1;k>=0;k--)if(ev.layers[k].name!=='ori_events'){ev.layers[k].locked=false;ev.layers[k].visible=true;ev.layers[k].remove();}
  for(var k=ev.pageItems.length-1;k>=0;k--){ev.pageItems[k].locked=false;ev.pageItems[k].remove();}
  var pale=ev.layers.add();pale.name='F-Event-Route';for(var i=0;i<run.segments.length;i++){var s=run.segments[i],p=line(pale,s.a,s.b,'#7FA4CB',1.7);p.opacity=40;}
  heading(ev,'02','EVENT MARKERS',id+' / geometric candidate order');for(var i=0;i<run.events.length;i++){var e=run.events[i],x=e.xy[0],y=e.xy[1];text(ev,e.event_id.substr(1),x+11,y+16,14,'#172B44');}
  text(ev,run.events.length+' original AI icons',1525,1150,18);text(ev,'001 = Spawn',1525,1108,16,'#167647');text(ev,'End has no event number',1525,1074,15);text(ev,'Geometry order only',1525,1028,15,'#9A5A16');text(ev,'Times/actions unverified',1525,996,15,'#9A5A16');
  view(doc,['F-Background','F-Walls','F-Movement-Labels']);var opts=new IllustratorSaveOptions();opts.pdfCompatible=true;var target=File(out.fsName+'/'+id+'_edited.ai');doc.saveAs(target,opts);doc.close(SaveOptions.DONOTSAVECHANGES);log.writeln('SAVED '+target.fsName);doc=app.open(target);log.writeln('REOPENED '+doc.layers.length);
  var checkWalls=top(doc,'F-Walls'),checkDetails=checkWalls&&child(checkWalls,'F-CAD-Details');
  if(!checkDetails||checkDetails.pageItems.length!==3){
    log.writeln('REPAIRING CAD details after reopen');
    checkWalls.locked=false;checkWalls.visible=true;
    if(checkDetails){checkDetails.locked=false;checkDetails.visible=true;checkDetails.remove();}
    checkDetails=checkWalls.layers.add();checkDetails.name='F-CAD-Details';
    for(var ci=0;ci<map.circles.length;ci++){var cp=[];for(var cj=0;cj<map.circles[ci][1].length;cj++)cp.push([map.circles[ci][1][cj][0],map.circles[ci][1][cj][1]-1500]);var circleItem=path(checkDetails,cp,null,'#D9AB00',1.8);circleItem.closed=true;}
    for(var pi=0;pi<map.polylines.length;pi++){var pp=[];for(var pj=0;pj<map.polylines[pi][1].length;pj++)pp.push([map.polylines[pi][1][pj][0],map.polylines[pi][1][pj][1]-1500]);var squareItem=path(checkDetails,pp,null,'#555D64',1.2);squareItem.closed=map.polylines[pi][2];}
    doc.saveAs(target,opts);doc.close(SaveOptions.DONOTSAVECHANGES);doc=app.open(target);
    checkDetails=child(top(doc,'F-Walls'),'F-CAD-Details');
    if(!checkDetails||checkDetails.pageItems.length!==3)throw Error('DXF details did not persist in '+id);
  }
  // The old linked image in hidden original is irrelevant to all six exported views.
  original=top(doc,'original');if(original){original.locked=false;original.visible=true;for(var k=0;k<original.layers.length;k++){original.layers[k].locked=false;original.layers[k].visible=true;}original.remove();}
  var views=[['movement',['F-Background','F-Walls','F-Movement-Labels']],['events',['F-Background','F-Walls','F-Event-Labels']],['convex',['F-Background','F-Walls','F-Choice-Labels']],['visibility',['F-Background','F-Walls','F-VGA-Labels']],['gate_counts',['F-Background','F-Walls','F-Gate-Counts-Labels']],['metric_distance',['F-Background','F-Walls','F-Metric-Labels']]];
  for(var k=0;k<views.length;k++){exportView(doc,out,views[k][0]+'_from_edited_ai',views[k][1]);log.writeln('EXPORTED '+views[k][0]);}
  doc.close(SaveOptions.DONOTSAVECHANGES);log.writeln('COMPLETE');log.close();
 }
})();
