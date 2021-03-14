// /static/index.js
console.log('Starting DocTagger')

var prevfile = "";
var test;
var dclick_e = null;

function tag_reader(e) {
    // use the docID to look up related tags and frequencies
    console.log("tag_reader started");
    docid = e.target.attributes.id.value
    e.preventDefault();
    $.getJSON('/tagreader/', {docid: '"' + docid + '"'}, function(data) {
        var mytag = "";
        console.log("/tag_reader Result - Docid = " + docid);
        $('#taglist').empty();
        prevtag = "";
        i = 1;
        $('#taglist').append('<thead><tr>'
                           + '<th scope="col">#</th>'
                           + '<th scope="col">Tag</th>'
                           + '<th scope="col">Freq</th>'
                           + '</tr></thead>'
                           + '<tbody>');
        for (mytag of data) {
            $('#taglist').append('<tr><th scope="row">' + i
                + '</th><td>' + mytag.tag
                + '</td><td>' + mytag.freq
                + '</td></tr>')
            i += 1;
        }
        $('#taglist').append('</tbody>');

        }
    )
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

function doc_reader(shared) {
    if (shared) {
        $.getJSON('/sharedreader/', function(data2) {
            var myfile = "";
            var mylist = "";    // debugging
            test = data2;        // debugging
            console.log("/sharedreader Request");
            $('#filelist').empty();
            $('#taglist').empty();
            prevfile = "";
            for (myfile of data2) {
                if (myfile.mimeType.includes(".folder")) {
                    $('#filelist').append('<li class="list-group-item" id="' + myfile.id + '">' +
                                        ' <i class="fa fa-fw fa-folder" style="color: gray"></i> ' + myfile.name + '</li>');
                    }
                    else {
                    $('#filelist').append('<li class="list-group-item" id="' + myfile.id + '">' +
                                        ' <i class="fa fa-fw fa-file" style="color: lightgray"></i> ' + myfile.name + '</li>');
                    }
            };
            loadFileListener();    // add click listeners
        })

    } else {        // TODO combine these two condition paths
        $.getJSON('/docreader/', function(data2) {
            var myfile = "";
            var mylist = "";    // debugging
            test = data2;        // debugging
            console.log("/docreader Request");
            $('#filelist').empty();
            $('#taglist').empty();
            prevfile = "";
            for (myfile of data2) {
                if (myfile.mimeType.includes(".folder")) {
                    $('#filelist').append('<li class="list-group-item" id="' + myfile.id + '">' +
                                        ' <i class="fa fa-fw fa-folder" style="color: gray"></i> ' + myfile.name + '</li>');
                    }
                    else {
                    $('#filelist').append('<li class="list-group-item" id="' + myfile.id + '">' +
                                        ' <i class="fa fa-fw fa-file" style="color: lightgray"></i> ' + myfile.name + '</li>');
                    }
            };
            loadFileListener();    // add click listeners
        })
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
