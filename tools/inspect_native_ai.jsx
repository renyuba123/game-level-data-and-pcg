(function () {
    var root=File($.fileName).parent.parent;
    var src=File(root.fsName+'/鼠王关玩家路线图001.ai');
    var out=File(root.fsName+'/runs/ratking_run-001/native_items.tsv');
    var doc=app.open(src);
    out.encoding='UTF-8'; out.open('w');
    out.writeln('layer\ttype\tuuid\tclosed\tfilled\tstroked\tanchors');
    for(var i=0;i<doc.pathItems.length;i++) {
        var p=doc.pathItems[i], anchors=[];
        for(var j=0;j<p.pathPoints.length;j++) anchors.push(p.pathPoints[j].anchor[0].toFixed(3)+':'+p.pathPoints[j].anchor[1].toFixed(3));
        var id=''; try { id=p.uuid; } catch(e) { id='unavailable'; }
        out.writeln(p.layer.name+'\tPathItem\t'+id+'\t'+p.closed+'\t'+p.filled+'\t'+p.stroked+'\t'+anchors.join(';'));
    }
    out.close(); doc.close(SaveOptions.DONOTSAVECHANGES);
})();
