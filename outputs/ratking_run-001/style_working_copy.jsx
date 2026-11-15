/* Illustrator 2026: File > Scripts > Other Script. Uses the original directly;
   writes one edited AI and figure exports derived from that edited document. */
(function () {
    var root = File($.fileName).parent.parent.parent;
    var input = File(root.fsName + '/鼠王关玩家路线图001.ai');
    var out = Folder(root.fsName + '/outputs/ratking_run-001');
    var edited = File(out.fsName + '/ratking_run-001_edited.ai');
    if (!input.exists) { alert('Original AI missing: ' + input.fsName); return; }
    if (edited.exists) { alert('Edited AI already exists; review it before rerunning.'); return; }
    var doc = app.open(input);
    function rgb(hex) { var c=new RGBColor(); c.red=parseInt(hex.substr(1,2),16); c.green=parseInt(hex.substr(3,2),16); c.blue=parseInt(hex.substr(5,2),16); return c; }
    function layer(name) { for(var i=0;i<doc.layers.length;i++) if(doc.layers[i].name===name) return doc.layers[i]; return null; }
    function label(target, text, x, y, size, color) {
        var t=target.textFrames.add(); t.contents=text; t.position=[x,y];
        t.textRange.characterAttributes.size=size; t.textRange.characterAttributes.fillColor=rgb(color); return t;
    }
    var base=layer('Base'), raw=layer('Route'), depth=layer('depthmap');
    if (!base || !raw || !depth) { alert('Base, Route or depthmap layer missing.'); doc.close(SaveOptions.DONOTSAVECHANGES); return; }
    var styled=doc.layers.add(); styled.name='Route Direction';
    var rawLock=raw.locked; raw.locked=false;
    for(var j=raw.pageItems.length-1;j>=0;j--) {
        var item=raw.pageItems[j]; if(item.locked) continue;
        var clone=item.duplicate(styled,ElementPlacement.PLACEATEND);
        if(clone.typename==='PathItem') { if(clone.stroked) { clone.strokeColor=rgb('#147DCE'); clone.strokeWidth=2.6; } }
        else if(clone.typename==='CompoundPathItem') for(var k=0;k<clone.pathItems.length;k++) if(clone.pathItems[k].stroked) { clone.pathItems[k].strokeColor=rgb('#147DCE'); clone.pathItems[k].strokeWidth=2.6; }
    }
    raw.visible=false; raw.locked=rawLock;
    var rect=doc.artboards[0].artboardRect, left=rect[0], bottom=rect[3];
    var rooms=doc.layers.add(); rooms.name='Room IDs (provisional)';
    var positions=[['R01',385,1100],['R02',560,1100],['R03',770,890],['R04',245,640],['R05',565,650],['R06',475,380],['R07',950,650],['R08',950,440],['R09',1145,600],['R10',1325,650]];
    for(var q=0;q<positions.length;q++) label(rooms,positions[q][0],left+positions[q][1],bottom+positions[q][2],22,'#34445A');
    var notes=doc.layers.add(); notes.name='Analysis Notes';
    label(notes,'Spawn / start (user confirmed)',left+668,bottom+902,14,'#16763D');
    label(notes,'End near Transform (user confirmed; exact marker pending)',left+150,bottom+770,13,'#713D9B');
    label(notes,'Route direction: Spawn to left endpoint; detailed junctions need review',left+40,bottom+1440,15,'#26384A');
    var legend=doc.layers.add(); legend.name='Legend';
    label(legend,'R01-R10: provisional convex-space IDs; verify against graph export',left+40,bottom+1400,13,'#34445A');
    label(legend,'Blue: route; green: Spawn; purple: Transform; no verified timestamps',left+40,bottom+1375,13,'#34445A');
    var save=new IllustratorSaveOptions(); save.pdfCompatible=true; doc.saveAs(edited,save);
    function figure(name,visible) {
        for(var i=0;i<doc.layers.length;i++) doc.layers[i].visible=false;
        for(var j=0;j<doc.layers.length;j++) for(var v=0;v<visible.length;v++) if(doc.layers[j].name===visible[v]) doc.layers[j].visible=true;
        var svg=new ExportOptionsSVG(); svg.embedRasterImages=true; svg.coordinatePrecision=3;
        doc.exportFile(File(out.fsName+'/'+name+'.svg'),ExportType.SVG,svg);
        var png=new ExportOptionsPNG24(); png.antiAliasing=true; png.transparency=false; png.artBoardClipping=true; png.horizontalScale=100; png.verticalScale=100;
        doc.exportFile(File(out.fsName+'/'+name+'.png'),ExportType.PNG24,png);
    }
    var events=[]; for(var e=0;e<doc.layers.length;e++) {
        var nm=doc.layers[e].name;
        if(nm!=='Base' && nm!=='Route' && nm!=='depthmap' && nm!=='Route Direction' && nm!=='Room IDs (provisional)' && nm!=='Analysis Notes' && nm!=='Legend') events.push(nm);
    }
    figure('movement_from_edited_ai',['depthmap','Base','Route Direction','Room IDs (provisional)','Analysis Notes','Legend']);
    figure('combat_from_edited_ai',['depthmap','Base','Route Direction','Room IDs (provisional)','Legend'].concat(events));
    figure('convex_from_edited_ai',['depthmap','Base','Room IDs (provisional)','Legend']);
    doc.close(SaveOptions.DONOTSAVECHANGES);
    alert('Saved edited AI and derived figures. Visibility/VGA export still requires data from shuwangguan.graph.');
})();
