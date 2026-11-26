/* Revise the user's saved edited AI in place. Never reconstruct event icons. */
(function(){
 var data=/*DATA_LITERAL*/null;
 var root=File($.fileName).parent.parent;
 var out=Folder(root.fsName+'/outputs/ratking_run-001');
 var ai=File(out.fsName+'/ratking_run-001_edited.ai');
 var log=File(out.fsName+'/figure_render.log');log.encoding='UTF-8';log.open('w');
 function note(s){log.writeln(s);}
 var doc=null;
 for(var openIndex=app.documents.length-1;openIndex>=0;openIndex--){
   var openDoc=app.documents[openIndex];
   if(openDoc.fullName.fsName.toLowerCase()===ai.fsName.toLowerCase()){
     if(!openDoc.saved){if(doc)throw Error('Multiple unsaved edited AI documents are open');doc=openDoc;}
     else openDoc.close(SaveOptions.DONOTSAVECHANGES);
   }
 }
 if(!doc)doc=app.open(ai);
 function find(n){for(var i=0;i<doc.layers.length;i++)if(doc.layers[i].name===n)return doc.layers[i];return null;}
 function child(parent,n){for(var i=0;i<parent.layers.length;i++)if(parent.layers[i].name===n)return parent.layers[i];return null;}
 function rgb(s){var c=new RGBColor();c.red=parseInt(s.substr(1,2),16);c.green=parseInt(s.substr(3,2),16);c.blue=parseInt(s.substr(5,2),16);return c;}
 function text(l,s,x,y,size,ink){var t=l.textFrames.add();t.contents=s;t.position=[x,y-1500];t.textRange.characterAttributes.size=size;t.textRange.characterAttributes.fillColor=rgb(ink||'#203044');return t;}
 function path(l,p,fill,stroke,sw,opacity){var a=l.pathItems.add();a.setEntirePath(p);a.closed=true;a.filled=!!fill;if(fill)a.fillColor=rgb(fill);a.stroked=!!stroke;if(stroke){a.strokeColor=rgb(stroke);a.strokeWidth=sw||1;}if(opacity!==undefined)a.opacity=opacity;return a;}
 function rect(l,x,top,w,h,fill,opacity){return path(l,[[x,top-1500],[x+w,top-1500],[x+w,top-h-1500],[x,top-h-1500]],fill,null,0,opacity);}
 function seg(l,x1,y1,x2,y2,color,width){var p=l.pathItems.add();p.setEntirePath([[x1,y1-1500],[x2,y2-1500]]);p.closed=false;p.filled=false;p.stroked=true;p.strokeColor=rgb(color);p.strokeWidth=width;return p;}
 function heading(l,n,title,subtitle){text(l,n+'  '+title,50,1224,27,'#172B44');text(l,subtitle,52,1194,14,'#4E5B6A');seg(l,1495,285,1495,1180,'#D3D9E0',1.2);}
 function number(n){var s=String(n),r='';for(var i=s.length-1,j=0;i>=0;i--,j++){if(j&&j%3===0)r=','+r;r=s.charAt(i)+r;}return r;}
 function clearDirect(l){for(var i=l.pageItems.length-1;i>=0;i--){l.pageItems[i].locked=false;l.pageItems[i].remove();}}
 var events=find('F-Event-Labels'),movement=find('F-Movement-Labels'),visibility=find('F-VGA-Labels'),choice=find('F-Choice-Labels');
 var walls=find('F-Walls'),paper=find('F-Background'),original=find('original');
 if(!original&&events&&movement&&visibility&&choice){
   original=doc.layers.add();original.name='original';
   var eventNames={'Death':true,'Break':true,'Brick':true,'Crossbow':true,'Hunting Pistol':true,
     'Pistol':true,'Shotgun':true,'Rifle':true,'Pipe Bomb':true,'Health damage':true,
     'Melee':true,'Flamethrower':true,'Transform':true};
   var baseNames={'Spawn':true,'Route':true,'Base':true,'depthmap':true};
   var iconsRoot=events.layers.add();iconsRoot.name='ori_events';
   var toEvents=[],toOriginal=[];
   for(var z=0;z<doc.layers.length;z++){
     var src=doc.layers[z];if(eventNames[src.name])toEvents.push(src);
     else if(baseNames[src.name])toOriginal.push(src);
   }
   events.locked=false;events.visible=true;iconsRoot.locked=false;iconsRoot.visible=true;original.locked=false;original.visible=true;
   function unlockLayer(l){l.locked=false;l.visible=true;for(var q=0;q<l.pageItems.length;q++)l.pageItems[q].locked=false;}
   for(var z=0;z<toEvents.length;z++){unlockLayer(toEvents[z]);toEvents[z].move(iconsRoot,ElementPlacement.PLACEATEND);}
   for(var z=0;z<toOriginal.length;z++){unlockLayer(toOriginal[z]);toOriginal[z].move(original,ElementPlacement.PLACEATEND);}
   var oldVGA=find('F-VGA');if(oldVGA){unlockLayer(visibility);unlockLayer(oldVGA);oldVGA.move(visibility,ElementPlacement.PLACEATEND);}
   var oldChoice=find('F-ConvexChoice');if(oldChoice){unlockLayer(choice);unlockLayer(oldChoice);oldChoice.move(choice,ElementPlacement.PLACEATEND);}
   var generic=find('F-Events');if(generic){generic.locked=false;generic.visible=true;generic.remove();}
   note('REBUILT label hierarchy from original native layers');
 }
 if(!events||!movement||!visibility||!choice||!walls||!paper||!original){var names=[];for(var z=0;z<doc.layers.length;z++)names.push(doc.layers[z].name);throw Error('Edited AI is missing a required saved layer; found '+names.join(','));}
 choice.locked=false;choice.visible=true;visibility.locked=false;visibility.visible=true;
 for(var i=0;i<choice.textFrames.length;i++)if(choice.textFrames[i].contents.indexOf('Depthmap+ Convex Map /')===0)
   choice.textFrames[i].contents='Depthmap+ Convex Map / 9 regions';
 for(var i=0;i<visibility.textFrames.length;i++)if(visibility.textFrames[i].contents.indexOf('Visual Integration [HH] /')===0)
   visibility.textFrames[i].contents='Visual Integration [HH] / 3,462 points';
 var icons=child(events,'ori_events'),originalSpawn=child(original,'Spawn');
 if(!icons||!originalSpawn||originalSpawn.pathItems.length!==1)throw Error('Original Spawn or ori_events missing');
 var nativeCount=0;
 for(var i=0;i<icons.layers.length;i++)if(icons.layers[i].name!=='Spawn')nativeCount+=icons.layers[i].pathItems.length;
 if(nativeCount!==23)throw Error('Expected 23 preserved ori_events icons');
 var spawnIcon=child(icons,'Spawn');if(!spawnIcon){spawnIcon=icons.layers.add();spawnIcon.name='Spawn';originalSpawn.pathItems[0].duplicate(spawnIcon,ElementPlacement.PLACEATEND);}
 if(spawnIcon.pathItems.length!==1)throw Error('Expected one duplicated native Spawn icon');
 function center(item){var b=item.geometricBounds;return [(b[0]+b[2])/2,(b[1]+b[3])/2+1500];}
 function auditIcons(){
   var found={},used={};
   for(var i=0;i<data.events.length;i++){
     var e=data.events[i],best=null,bestD=1e20,bestItem=null;
     for(var j=0;j<icons.layers.length;j++)if(icons.layers[j].name===e[1])
       for(var k=0;k<icons.layers[j].pathItems.length;k++){
         var item=icons.layers[j].pathItems[k],p=center(item),d=Math.sqrt(Math.pow(p[0]-e[3],2)+Math.pow(p[1]-e[4],2));
         if(d<bestD){bestD=d;bestItem=item;}
       }
     if(!bestItem||bestD>40||used[String(bestItem.uuid)])throw Error('Icon geometry mismatch '+e[0]+' distance '+bestD);
     used[String(bestItem.uuid)]=true;found[e[0]]=[e[2],String(bestItem.uuid),bestD];
   }
   return found;
 }
 var iconAudit=auditIcons();note('VERIFIED '+nativeCount+' original ori_events icons plus copied Spawn by layer and geometry');
 events.locked=false;events.visible=true;movement.locked=false;movement.visible=true;
 // Parent layers own their category graphics. The common walls and paper remain shared.
 var oldRoute=find('F-Route'),movementRoute=child(movement,'F-Movement-Route');
 if(!movementRoute){
   var looseRoute=find('F-Movement-Route');
   if(looseRoute&&looseRoute.pageItems.length===60){
     looseRoute.locked=false;looseRoute.visible=true;
     for(var t=0;t<looseRoute.pageItems.length;t++)looseRoute.pageItems[t].locked=false;
     looseRoute.move(movement,ElementPlacement.PLACEATEND);
     movementRoute=child(movement,'F-Movement-Route');
   }else{
     if(!oldRoute||oldRoute.pageItems.length!==60)throw Error('Missing the 60 saved route items');
     movementRoute=movement.layers.add();movementRoute.name='F-Movement-Route';
     for(var i=0;i<oldRoute.pageItems.length;i++)oldRoute.pageItems[i].duplicate(movementRoute,ElementPlacement.PLACEATEND);
     if(movementRoute.pageItems.length!==60)throw Error('Route copy incomplete');
     oldRoute.locked=false;oldRoute.visible=true;oldRoute.remove();
   }
 }
 var pale=child(events,'F-Event-Route');if(pale){pale.locked=false;pale.visible=true;pale.remove();}
 pale=events.layers.add();pale.name='F-Event-Route';
 for(var i=0;i<movementRoute.pageItems.length;i++){
   var copy=movementRoute.pageItems[i].duplicate(pale,ElementPlacement.PLACEATEND);copy.opacity=25;
 }
 if(pale.pageItems.length!==movementRoute.pageItems.length)throw Error('Event route copy incomplete');
 clearDirect(events);
 heading(events,'02','EVENT MARKERS','run-001 / candidate route order');
 for(var i=0;i<data.events.length;i++){
   var e=data.events[i],label=e[0].substr(1),x=e[3],y=e[4],lx=e[5],ly=e[6];
   seg(events,x,y,lx+12,ly+5,'#8994A2',0.8);
   rect(events,lx-3,ly+17,47,26,'#FFFFFF',95);
   text(events,label,lx,ly+12,16,'#172B44');
 }
 text(events,'Original AI icons',1525,1150,21);
 text(events,'001 = Spawn / route start',1525,1108,16,'#167647');
 text(events,'024 = final icon near End',1525,1074,16,'#394A61');
 text(events,'End is a route label',1525,1040,16,'#7846A5');
 text(events,'24 marks / 9 source layers',1525,980,16);
 text(events,'IDs follow the drawn route',1525,942,16);
 text(events,'Local order: candidate only',1525,910,16,'#9A5A16');
 text(events,'Action times unverified',1525,878,16,'#9A5A16');
 text(events,'One icon outside convex',1525,814,16,'#9A5A16');
 text(events,'polygon: 012 / Flamethrower',1525,782,16,'#9A5A16');
 text(events,'Source: ori_events + Spawn',1525,630,15);
 text(events,'Icon shapes unchanged',1525,600,15);
 text(events,'No event rate inferred',1525,570,15);
 var gate=find('F-Gate-Counts-Labels');if(gate){gate.locked=false;gate.visible=true;gate.remove();}
 gate=doc.layers.add();gate.name='F-Gate-Counts-Labels';
 var gateMap=gate.layers.add();gateMap.name='F-Gate-Counts';
 var bands=data.gate_palette,gateBandCounts=[];
 for(var i=0;i<bands.colors.length;i++)gateBandCounts.push(0);
 for(var i=0;i<data.gate_points.length;i++){
   var gp=data.gate_points[i],band=0;
   while(band+1<bands.colors.length&&gp[2]>=bands.lower_bounds_inclusive[band+1])band++;
   rect(gateMap,gp[0]-5.3,gp[1]+5.3,10.6,10.6,bands.colors[band]);
   gateBandCounts[band]++;
 }
 if(gateMap.pathItems.length!==data.gate_point_count)throw Error('Gate cell count mismatch');
 heading(gate,'05','VGA GATE COUNTS','run-001 / value-calibrated vector map');
 text(gate,'Gate Counts',1525,1150,23);
 text(gate,'3,462 VGA points / count',1525,1112,16);
 text(gate,'Range: 4 - 7,230',1525,1082,16);
 text(gate,'10 image-matched bands',1525,1035,17,'#167647');
 for(var i=0;i<bands.colors.length;i++){
   var y=998-i*51;
   rect(gate,1525,y+13,24,24,bands.colors[i]);
   text(gate,number(bands.lower_bounds_inclusive[i])+' - '+number(bands.upper_bounds_inclusive[i]),1564,y+4,15);
 }
 text(gate,'Derived bands: original',1525,460,15);
 text(gate,'Depthmap image + VGA TXT',1525,432,15);
 text(gate,'Native thresholds unverified',1525,391,14,'#9A5A16');
 text(gate,'Not player traversal count',1525,353,14,'#9A5A16');
 text(gate,'Physical scale unverified',1525,325,14);
 note('GATE vector cells '+gateMap.pathItems.length+' bands '+gateBandCounts.join(',')+' calibrated to '+data.gate_image_sha256);
 function setView(names){for(var i=0;i<doc.layers.length;i++)doc.layers[i].visible=false;
   for(var i=0;i<names.length;i++){var l=find(names[i]);if(!l)throw Error('Missing view layer '+names[i]);l.visible=true;}}
 setView(['F-Background','F-Walls','F-Movement-Labels']);
 var opts=new IllustratorSaveOptions();opts.pdfCompatible=true;doc.saveAs(ai,opts);note('SAVED '+ai.fsName);
 doc.close(SaveOptions.DONOTSAVECHANGES);doc=app.open(ai);note('REOPENED '+doc.layers.length);
 events=find('F-Event-Labels');icons=child(events,'ori_events');iconAudit=auditIcons();
 var auditFile=File(out.fsName+'/icon_audit.tsv');auditFile.encoding='UTF-8';auditFile.open('w');
 auditFile.writeln('event_id\tsource_original_ai_uuid\tedited_ai_uuid\tcentroid_offset_ai_pt');
 for(var i=0;i<data.events.length;i++){var e=data.events[i],a=iconAudit[e[0]];auditFile.writeln(e[0]+'\t'+a[0]+'\t'+a[1]+'\t'+a[2].toFixed(3));}
 auditFile.close();note('AUDITED icons after AI reopen');
 // Hidden original depthmap links otherwise leak into exported SVGs.
 var exportSource=find('original');exportSource.visible=true;exportSource.locked=false;
 for(var k=0;k<exportSource.layers.length;k++){exportSource.layers[k].visible=true;exportSource.layers[k].locked=false;}
 exportSource.remove();
 function exportView(name,names){setView(names);
   var svg=new ExportOptionsSVG();svg.embedRasterImages=true;svg.coordinatePrecision=3;
   svg.fontSubsetting=SVGFontSubsetting.GLYPHSUSED;svg.fontType=SVGFontType.OUTLINEFONT;
   doc.exportFile(File(out.fsName+'/'+name+'.svg'),ExportType.SVG,svg);
   var png=new ExportOptionsPNG24();png.antiAliasing=true;png.transparency=false;png.artBoardClipping=true;png.horizontalScale=100;png.verticalScale=100;
   doc.exportFile(File(out.fsName+'/'+name+'.png'),ExportType.PNG24,png);note('EXPORTED '+name);}
 exportView('movement_from_edited_ai',['F-Background','F-Walls','F-Movement-Labels']);
 exportView('combat_from_edited_ai',['F-Background','F-Walls','F-Event-Labels']);
 exportView('convex_from_edited_ai',['F-Background','F-Walls','F-Choice-Labels']);
 exportView('visibility_from_edited_ai',['F-Background','F-Walls','F-VGA-Labels']);
 exportView('gate_counts_from_edited_ai',['F-Background','F-Walls','F-Gate-Counts-Labels']);
 doc.close(SaveOptions.DONOTSAVECHANGES);log.close();
})();
