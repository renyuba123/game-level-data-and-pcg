(function(){
 var root=File($.fileName).parent.parent, names=['source/illustrator/鼠王关玩家路线图001.ai','source/illustrator/002.ai','source/illustrator/003_.ai','source/illustrator/004.ai','source/illustrator/005_.ai','outputs/ratking_run-001/ratking_run-001_edited.ai','outputs/ratking_run-001/ratking_run-source/illustrator/002.ai'];
 var log=File(root.fsName+'/outputs/native_inventory_001_005.tsv');log.encoding='UTF-8';log.open('w');
 log.writeln('file\tlayer_path\tdirect_paths\tall_paths\ttext_frames\tpage_items');
 function visit(file,layer,prefix){var path=prefix?prefix+'/'+layer.name:layer.name;log.writeln(file+'\t'+path+'\t'+layer.pathItems.length+'\t'+layer.pageItems.length+'\t'+layer.textFrames.length+'\t'+layer.pageItems.length);for(var j=0;j<layer.layers.length;j++)visit(file,layer.layers[j],path);}
 for(var i=0;i<names.length;i++){
  var file=File(root.fsName+'/'+names[i]);if(!file.exists){log.writeln(names[i]+'\tMISSING');continue;}
  var doc=app.open(file);for(var k=0;k<doc.layers.length;k++)visit(names[i],doc.layers[k],'');doc.close(SaveOptions.DONOTSAVECHANGES);
 }
 log.close();
})();
