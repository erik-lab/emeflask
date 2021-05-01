// /static/index.js
console.log('Starting minder');

var object_data = {};
var tag_data = {};

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
                + '<td scope="row" width="200px">' + row.object
                + '</td><td width="20px">' + row.source
                + '</td><td width="20px">' + row.tag_freq
                + '</td></tr>');
            }
        }
}


function load_tags() {
        // clear the html table
        var object_list = document.getElementById("tagtable");
        clear_table(object_list);
//        console.log("tag_data.tag[0]: ", tag_data.tag[0]);

        // reload the tag list

        for (row of tag_data) {
            // add all the tag rows
            $('#tagtable').append('<tr>'
            + '<td scope="row" width="200px">' + row.name
            + '</td><td width="20px">' + row.tag_freq
            + '</td></tr>');
        }
}


function go_button() {
    console.log("go_button");
//    console.log("go_button");

    user_thought = $("#thought")
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
        tag_data = data[1].tags;

        // load the visible table
        load_objects();
        load_tags();

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


function init(e) {
    console.log("running init()");
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

