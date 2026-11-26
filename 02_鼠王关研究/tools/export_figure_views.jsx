(function(){
 var root=File($.fileName).parent.parent;
 var out=Folder(root.fsName+'/outputs/ratking_run-001');
 var ai=File(out.fsName+'/ratking_run-001_edited.ai');
 var exportLog=File(out.fsName+'/figure_export.log');exportLog.encoding='UTF-8';exportLog.open('w');exportLog.writeln('SOURCE '+ai.fsName);exportLog.close();
 for(var openIndex=app.documents.length-1;openIndex>=0;openIndex--){
   var openDoc=app.documents[openIndex];
   if(openDoc.fullName.fsName.toLowerCase()===ai.fsName.toLowerCase()){
     if(!openDoc.saved)throw Error('Edited AI has unsaved changes; export only after saving it');
     openDoc.close(SaveOptions.DONOTSAVECHANGES);
   }
 }
 var d=app.open(ai);
 function find(n){for(var i=0;i<d.layers.length;i++)if(d.layers[i].name===n)return d.layers[i];throw Error('Missing '+n);}
 // Illustrator exports hidden linked raster images too. Remove the source-only
 // layer from this in-memory export document; the saved AI remains untouched.
 var source=find('original');source.visible=true;source.locked=false;
 for(var j=0;j<source.layers.length;j++){source.layers[j].visible=true;source.layers[j].locked=false;}
 source.remove();
 function note(s){var f=File(out.fsName+'/figure_export.log');f.encoding='UTF-8';f.open('a');f.writeln(s);f.close();}
 function view(name,names){for(var i=0;i<d.layers.length;i++)d.layers[i].visible=false;
  for(var i=0;i<names.length;i++)find(names[i]).visible=true;
  var svg=new ExportOptionsSVG();svg.embedRasterImages=true;svg.coordinatePrecision=3;
  svg.fontSubsetting=SVGFontSubsetting.GLYPHSUSED;svg.fontType=SVGFontType.OUTLINEFONT;
  d.exportFile(File(out.fsName+'/'+name+'.svg'),ExportType.SVG,svg);note('SVG '+name);
  var png=new ExportOptionsPNG24();png.antiAliasing=true;png.transparency=false;png.artBoardClipping=true;png.horizontalScale=100;png.verticalScale=100;
  d.exportFile(File(out.fsName+'/'+name+'.png'),ExportType.PNG24,png);note('PNG '+name);}
 view('movement_from_edited_ai',['F-Background','F-Walls','F-Movement-Labels']);
 view('combat_from_edited_ai',['F-Background','F-Walls','F-Event-Labels']);
 view('convex_from_edited_ai',['F-Background','F-Walls','F-Choice-Labels']);
 view('visibility_from_edited_ai',['F-Background','F-Walls','F-VGA-Labels']);
 view('gate_counts_from_edited_ai',['F-Background','F-Walls','F-Gate-Counts-Labels']);
 d.close(SaveOptions.DONOTSAVECHANGES);note('COMPLETE');
})();
