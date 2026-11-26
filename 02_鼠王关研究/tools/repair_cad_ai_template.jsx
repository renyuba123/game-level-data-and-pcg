/* Draw the three DXF non-LINE entities directly in each edited AI wall layer. */
(function(){
 var details=/*DETAILS_LITERAL*/null,root=File($.fileName).parent.parent;
 function color(hex){var c=new RGBColor();c.red=parseInt(hex.substr(1,2),16);c.green=parseInt(hex.substr(3,2),16);c.blue=parseInt(hex.substr(5,2),16);return c;}
 function top(doc,name){for(var i=0;i<doc.layers.length;i++)if(doc.layers[i].name===name)return doc.layers[i];return null;}
 function path(layer,points,name,stroke,width){var p=layer.pathItems.add();p.name=name;p.setEntirePath(points);p.closed=true;p.filled=false;p.stroked=true;p.strokeColor=color(stroke);p.strokeWidth=width;}
 for(var run=1;run<=5;run++){
  var id='ratking_run-00'+run,file=File(root.fsName+'/outputs/'+id+'/'+id+'_edited.ai'),doc=app.open(file),walls=top(doc,'F-Walls');
  if(!walls)throw Error('Missing F-Walls in '+id);
  walls.locked=false;walls.visible=true;
  for(var i=walls.layers.length-1;i>=0;i--)if(walls.layers[i].name==='F-CAD-Details'){walls.layers[i].locked=false;walls.layers[i].visible=true;walls.layers[i].remove();}
  for(var i=walls.pathItems.length-1;i>=0;i--)if(walls.pathItems[i].name.indexOf('DXF-CAD-DETAIL-')===0){walls.pathItems[i].locked=false;walls.pathItems[i].remove();}
  for(var i=0;i<details.circles.length;i++){var points=[];for(var j=0;j<details.circles[i][1].length;j++)points.push([details.circles[i][1][j][0],details.circles[i][1][j][1]-1500]);path(walls,points,'DXF-CAD-DETAIL-CIRCLE-'+(i+1),'#D9AB00',1.8);}
  for(var i=0;i<details.polylines.length;i++){var pts=[];for(var j=0;j<details.polylines[i][1].length;j++)pts.push([details.polylines[i][1][j][0],details.polylines[i][1][j][1]-1500]);path(walls,pts,'DXF-CAD-DETAIL-BOX-'+(i+1),'#555D64',1.2);}
  doc.save();doc.close(SaveOptions.DONOTSAVECHANGES);
 }
})();
