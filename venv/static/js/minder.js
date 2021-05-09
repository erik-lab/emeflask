// /static/index.js
console.log('Starting minder');

var object_data = {};
var rel_data = {};
var fillColors = {'doc': 'orange', 'thought': 'lightgreen'};
var strength_scale;

function clear_table(table) {
    // Preserve the header row
    for (var i = 1;i<table.rows.length;){
            table.deleteRow(i);
        }
}


function load_objects() {
        // clear the html table
        var object_list = document.getElementById("doctable");
        clear_table(object_list);

        // find what object type is selected
        obj_selected = $("#objects").val();
        if (obj_selected == 'documents') {
            lookfor = 'doc';
        }
        else if (obj_selected == 'emails') {
            lookfor = 'email'
        }
        else {
            lookfor = 'other'
        }

        // reload the visible object type

        for (row of object_data) {
            // if the row is of the right type, then add it, else
            if (row.type == lookfor) {
                $('#doctable').append('<tr>'
                + '<td scope="row" width="200px" class="draggable" draggable="true">' + row.object
                + '</td><td width="20px">' + row.source
                + '</td><td width="20px">' + row.tag_freq
                + '</td></tr>');
            }
            // whether looked for or not, add to the relationship diagram
//            window.myDiagram.layout.isInitial = true;
//            window.myDiagram.layout.isOngoing = true;
            window.myDiagram.model.linkDataArray = [{}];
            window.myDiagram.model.nodeDataArray = [{}];
            window.myDiagram.model.nodeDataArray = object_data;
        }
}


function load_assocs() {
        // clear the html table
        var object_list = document.getElementById("reltable");
//        clear_table(object_list);
//        console.log("rel_data: ", rel_data);

        // reload the rel list
        // first get the max strength and compute scaling factor
        if (rel_data.length > 0) {maxstr = rel_data[0].strength} else {maxstr = 100}
        strength_scale = (maxstr / 3).toFixed();
        console.log("strength_scale = ", strength_scale);

        for (row of rel_data) {
            // add all the rel rows
            $('#reltable').append('<tr>'
            + '<td scope="row" width="200px">' + row.name1
            + '<td scope="row" width="200px">' + row.name2
            + '</td><td width="20px">' + row.strength
            + '</td></tr>');
            // add the links to the relationship diagram
            window.myDiagram.model.linkDataArray = [{}];
            window.myDiagram.model.linkDataArray = rel_data;
        }
}


function go_button() {
    console.log("go_button");
//    console.log("go_button");

    user_thought = $("#thought")
    console.log("thought", user_thought.val())
    tags = user_thought.val().split(" ");

//     console.log(tags);

    //  Add other contextual tags
    //  like what?  Last go?  previous thought? What's New?

    //  Now call the go endpoint to get all related objects
    var tdata = {};
    for (var i = 0; i < tags.length; i++) {
        tdata["t"+i] = tags[i];
    }
    tdata['len'] = i;

    $.getJSON('/minder/go/obj', tdata, function(data) {
        console.log("/minder_go_obj Result ", data);

        // store the full data set for reference
        object_data = data[0].objs;
        rel_data = data[1].rels;

        // load the visible table
        load_objects();
        load_assocs();

        // Get the doc related tags
//        $.getJSON('/minder/go/tags', function(data2) {
//            console.log("/minder_go_tags Result ", data2);
//
//            // store the full data set for reference
//            tag_data = data2;
//            // load the visible table
//            load_tags();
//        })
    })
}

// This variation on ForceDirectedLayout does not move any selected Nodes
// but does move all other nodes (vertexes).
function ContinuousForceDirectedLayout() {
  go.ForceDirectedLayout.call(this);
  this._isObserving = false;
}
go.Diagram.inherit(ContinuousForceDirectedLayout, go.ForceDirectedLayout);

ContinuousForceDirectedLayout.prototype.isFixed = function(v) {
  return v.node.isSelected;
}

// optimization: reuse the ForceDirectedNetwork rather than re-create it each time
ContinuousForceDirectedLayout.prototype.doLayout = function(coll) {
  if (!this._isObserving) {
    this._isObserving = true;
    // cacheing the network means we need to recreate it if nodes or links have been added or removed or relinked,
    // so we need to track structural model changes to discard the saved network.
    var lay = this;
    this.diagram.addModelChangedListener(function(e) {
      // modelChanges include a few cases that we don't actually care about, such as
      // "nodeCategory" or "linkToPortId", but we'll go ahead and recreate the network anyway.
      // Also clear the network when replacing the model.
      if (e.modelChange !== "" ||
        (e.change === go.ChangedEvent.Transaction && e.propertyName === "StartingFirstTransaction")) {
        lay.network = null;
      }
    });
  }
  var net = this.network;
  if (net === null) {  // the first time, just create the network as normal
    this.network = net = this.makeNetwork(coll);
  } else {  // but on reuse we need to update the LayoutVertex.bounds for selected nodes
    this.diagram.nodes.each(function(n) {
      var v = net.findVertex(n);
      if (v !== null) v.bounds = n.actualBounds;
    });
  }
  // now perform the normal layout
  go.ForceDirectedLayout.prototype.doLayout.call(this, coll);
  // doLayout normally discards the LayoutNetwork by setting Layout.network to null;
  // here we remember it for next time
  this.network = net;
}
// end ContinuousForceDirectedLayout


function init(e) {
    console.log("running init()");

    // *********************************************************
    // First, set up the infrastructure to do HTML drag-and-drop
    // *********************************************************

    var dragged = null; // A reference to the element currently being dragged

    // highlight stationary nodes during an external drag-and-drop into a Diagram
    function highlight(node) {  // may be null
    var oldskips = myDiagram.skipsUndoManager;
    myDiagram.skipsUndoManager = true;
    myDiagram.startTransaction("highlight");
    if (node !== null) {
      myDiagram.highlight(node);
    } else {
      myDiagram.clearHighlighteds();
    }
    myDiagram.commitTransaction("highlight");
    myDiagram.skipsUndoManager = oldskips;
    }

    // This event should only fire on the drag targets.
    // Instead of finding every drag target,
    // we can add the event to the document and disregard
    // all elements that are not of class "draggable"
    document.addEventListener("dragstart", function(event) {
        if (event.target.className !== "draggable") return;
        // Some data must be set to allow drag
        event.dataTransfer.setData("text", event.target.textContent);

        // store a reference to the dragged element and the offset of the mouse from the center of the element
        dragged = event.target;
        dragged.offsetX = event.offsetX - dragged.clientWidth / 2;
        dragged.offsetY = event.offsetY - dragged.clientHeight / 2;
        // Objects during drag will have a red border
        event.target.style.border = "2px solid red";
    }, false);

    // This event resets styles after a drag has completed (successfully or not)
    document.addEventListener("dragend", function(event) {
        // reset the border of the dragged element
        dragged.style.border = "";
        highlight(null);
    }, false);

    // Next, events intended for the drop target - the Diagram div

    var div = document.getElementById("myDiagramDiv");
    div.addEventListener("dragenter", function(event) {
        // Here you could also set effects on the Diagram,
        // such as changing the background color to indicate an acceptable drop zone

        // Requirement in some browsers, such as Internet Explorer
        event.preventDefault();
    }, false);

    div.addEventListener("dragover", function(event) {
        // We call preventDefault to allow a drop
        // But on divs that already contain an element,
        // we want to disallow dropping

        if (this === myDiagram.div) {
          var can = event.target;
          var pixelratio = myDiagram.computePixelRatio();

          // if the target is not the canvas, we may have trouble, so just quit:
          if (!(can instanceof HTMLCanvasElement)) return;

          var bbox = can.getBoundingClientRect();
          var bbw = bbox.width;
          if (bbw === 0) bbw = 0.001;
          var bbh = bbox.height;
          if (bbh === 0) bbh = 0.001;
          var mx = event.clientX - bbox.left * ((can.width / pixelratio) / bbw);
          var my = event.clientY - bbox.top * ((can.height / pixelratio) / bbh);
          var point = myDiagram.transformViewToDoc(new go.Point(mx, my));
          var curnode = myDiagram.findPartAt(point, true);
          if (curnode instanceof go.Node) {
            highlight(curnode);
          } else {
            highlight(null);
          }
        }

        if (event.target.className === "dropzone") {
          // Disallow a drop by returning before a call to preventDefault:
          return;
        }

        // Allow a drop on everything else
        event.preventDefault();
    }, false);

    div.addEventListener("dragleave", function(event) {
        // reset background of potential drop target
        if (event.target.className == "dropzone") {
          event.target.style.background = "";
        }
        highlight(null);
    }, false);

    div.addEventListener("drop", function(event) {
        // prevent default action
        // (open as link for some elements in some browsers)
        event.preventDefault();

        // Dragging onto a Diagram
        if (this === myDiagram.div) {
          var can = event.target;
          var pixelratio = myDiagram.computePixelRatio();
          console.log("dropped on the diagram")

          // if the target is not the canvas, we may have trouble, so just quit:
          if (!(can instanceof HTMLCanvasElement)) return;

          var bbox = can.getBoundingClientRect();
          var bbw = bbox.width;
          if (bbw === 0) bbw = 0.001;
          var bbh = bbox.height;
          if (bbh === 0) bbh = 0.001;
          var mx = event.clientX - bbox.left * ((can.width / pixelratio) / bbw) - dragged.offsetX;
          var my = event.clientY - bbox.top * ((can.height / pixelratio) / bbh) - dragged.offsetY;
          var point = myDiagram.transformViewToDoc(new go.Point(mx, my));
          myDiagram.startTransaction('new node');
          myDiagram.model.addNodeData({
            key: "8788hhghghghklll",
            object: event.dataTransfer.getData("text"),
            type: "thought",
            source: "EME",
            tag_freq: 2,
            location: point,
            text: event.dataTransfer.getData('text'),
            color: "lightyellow"
          });
          console.log("event data", event.dataTransfer);
          console.log("event data txt", event.dataTransfer.getData("text"));
          console.log("event data class", event.dataTransfer.getData("id"));
          myDiagram.commitTransaction('new node');

        }

        // If we were using drag data, we could get it here, ie:
        // var data = event.dataTransfer.getData('text');
    }, false);

    // *********************************************************
    // Second, set up a GoJS Diagram
    // *********************************************************


    var $g = go.GraphObject.make;  // for conciseness in defining templates
    
    myDiagram =
    $g(go.Diagram, "myDiagramDiv",  // must name or refer to the DIV HTML element
      {
        "undoManager.isEnabled": true,
        initialAutoScale: go.Diagram.Uniform,   // an initial automatic zoom-to-fit
        contentAlignment: go.Spot.Center,       // align document to the center of the viewport
        layout:
          $g(ContinuousForceDirectedLayout,  // automatically spread nodes apart while dragging
            { defaultSpringLength: 10, defaultElectricalCharge: -50 }),
        // do an extra layout at the end of a move
        "SelectionMoved": function(e) { e.diagram.layout.invalidateLayout(); }
      });
    
    // dragging a node invalidates the Diagram.layout, causing a layout during the drag
    myDiagram.toolManager.draggingTool.doMouseMove = function() {
        go.DraggingTool.prototype.doMouseMove.call(this);
        if (this.isActive) { this.diagram.layout.invalidateLayout(); }
    }
    
    // define each Node's appearance
    myDiagram.nodeTemplate =
    $g(go.Node, "Auto",  // the whole node panel
      // define the node's outer shape, which will surround the TextBlock
      $g(go.Shape, "Rectangle",
        { stroke: "black", spot1: new go.Spot(0, 0, 5, 5), spot2: new go.Spot(1, 1, -5, -5) },
        new go.Binding("fill", "type", function (t){ return fillColors[t] || "lightblue"; } )),
      $g(go.TextBlock,
        { font: "7pt helvetica, arial, sans-serif", textAlign: "center", maxSize: new go.Size(100, NaN) },
        new go.Binding("text", "object"))
    );
    // the rest of this app is the same as samples/conceptMap.html
    
    // replace the default Link template in the linkTemplateMap
    myDiagram.linkTemplate =
    $g(go.Link,  // the whole link panel
      $g(go.Shape,  // the link shape
        { stroke: "black" },
        new go.Binding("strokeWidth", "strength", function (s){ return Math.max(1,(2*(s / strength_scale).toFixed()))}))
    );
    
    // create the model for the concept map
    var nodeDataArray = [
    { key: "asdjasdlkjasdlkj", object: "Concept Maps", type: "thought", source: "Google Drive", tag_freq: 2 },
    { key: "asdasdasdasd", object: "object", type: "doc", source: "Google Drive", tag_freq: 2 },
//    { key: "asd987asd987", object: "Context Dependent", type: null, source: "Google Drive", tag_freq: 2 },
//    { key: "apa89e87rnfusdfsdfsdf", object: "Concepts", type: null, source: "Google Drive", tag_freq: 2 },

    ];
    var linkDataArray = [
    { from: "asdjasdlkjasdlkj", to: "asdasdasdasd", fname: "represent", tname: "asdasasd", strength: 1},
    { from: "asdasdasdasd", to: "apa89e87rnfusdfsdfsdf", fname: "represent", tname: "asdasasd", strength: 2},
    { from: "asdjasdlkjasdlkj", to: "asd987asd987", fname: "represent", tname: "asdasasd", strength: 3},
    { from: "asd987asd987", to: "asdasdasdasd", fname: "represent", tname: "asdasasd", strength: 4},


    ];
    myDiagram.model = new go.GraphLinksModel(nodeDataArray, linkDataArray);
 }
// end of Init

function reload() {
    //myDiagram.layout.network = null;
    var text = myDiagram.model.toJson();
    myDiagram.model = go.Model.fromJson(text);
    //myDiagram.layout =
    //  go.GraphObject.make(ContinuousForceDirectedLayout,  // automatically spread nodes apart while dragging
    //    { defaultSpringLength: 30, defaultElectricalCharge: 100 });
}

function click_action() {
    console.log("click_action: " + dclick_e);
    if (dclick_e == null) {
        return;
    }
    e = dclick_e;
    dclick_e = null;

    if (prevfile > "") {
        document.getElementById(prevfile.toString()).style.backgroundColor = "white";
    }
    document.getElementById(e.target.attributes.id.value.toString()).style.backgroundColor = "lightCyan";
    prevfile = e.target.attributes.id.value;

    tag_reader(e);
}

function doubleclick_action(e) {
    console.log("doubleclick: " + dclick_e);
}

function fileClick(e){
    console.log("fileClick");
    if (dclick_e != null) {
        e = dclick_e;
        dclick_e = null;
        doubleclick_action(e)   // Do Double click actions with original e
    } else {
        dclick_e = e
        setTimeout(click_action, 200);
    }
}

function loadFileListener(){
    var li = document.getElementsByTagName("ul");
    for (var i = 0; i<li.length; i++){
         li[i].addEventListener("click", fileClick);
    }
}


function do_connect(e) {
    // first wait for the connection to complete then request and load root files
    // TODO hand error condition
    console.log("do_connect started");

    e.preventDefault();
   // var deferral = $.Deferred();
    console.log("/Connect Request");
    $.getJSON('/connect/',
        function(data) {
            $("#dbconnectInd").text('Database ' + data.dbstatus);
            $("#accountInd").text('Account: ' + data.account);
            console.log("/Connect Updates");

            doc_reader();   // conect success - now get docs
            }
    );
    $("a.isDisabled").removeClass("isDisabled")
    $("a#connect").addClass("isDisabled")

    return false;
};

