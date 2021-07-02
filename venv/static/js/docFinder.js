// /static/index.js
console.log('Starting DocFinder')

var prevfile = "";
var test;
var dclick_e = null;
var viewtype = 'default';

function init(e) {
    console.log("running init()");

    var docs = [];

//    $('#doctable').DataTable();
//
    load_docs();
 }


function load_docs(e) {
    console.log("/finder_view");

    if ($("#includeShared").is(":checked")) {
        option = "IncludeShared"}
    else {
        option = "NoShared"}

    options = {options: option};

    console.log("options:", options);

    var ajax = new XMLHttpRequest();
    ajax.open("GET", "/finder/view/", true);
    ajax.onreadystatechange = function() {
        console.log("this.readystate & Status:", this.readyState, this.status)
        if (this.readyState == 4 && this.status == 200) {
            var data = JSON.parse(this.responseText);
            var values = [];
            var i = 0;
            for (row of data) {
                mt = row.mimeType.split("/");
                mtEnd = mt[1].split(".");
//                console.log("Mime type", row.mimeType, mtEnd[mtEnd.length - 1]);

                if ( row.source == "Google Drive" ) {
                    row.name = '<a href="https://docs.google.com/file/d/' + row.id + '/edit?usp=sharing"' +
                    'target="_blank" rel="noopener noreferrer">' + row.name + '</a>';
                }
                values[i] = [row.id, row.account, row.source, row.parent, row.name, row.modified,
                             mtEnd[mtEnd.length - 1], row.shared_to];
                i += 1;
            }
//            console.log("ajax response values", values);
            $('#doctable').DataTable( {
                data: values,
                columns: [
                    { title: "Id", visible: false},
                    { title: "Account" },
                    { title: "Source" },
                    { title: "Folder" },
                    { title: "Name" },
                    { title: "Modified" },
                    { title: "Mime Type" },
                    { title: "Shared" }
                ]
            } );

            var table = $('#doctable').DataTable();

            table.columns().flatten().each( function ( colIdx ) {
                // Create the select list and search operation
                var select = $('<br><select />')
                    .appendTo(
                        table.column(colIdx).footer()
                    )
                    .on( 'change', function () {
                        if ($(this).val() == 'All') {
                            table
                                .column( colIdx )
                                .search('')
                                .draw();
                        }
                        else {
                            table
                                .column( colIdx )
                                .search( $(this).val() )
                                .draw();
                        }
                    } );

                // Get the search data for the first column and add to the select list
                table
                    .column( colIdx )
                    .cache( 'search' )
                    .sort()
                    .unique()
                    .each( function ( d ) {
                        select.append( $('<option value="'+d+'">'+d+'</option>') );
                    } );

                select.prepend( $('<option value="All">All</option>') );
                select.val("All");
            } );
        }
    };
    ajax.send("somethings");

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
    // TODO handle error condition
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

