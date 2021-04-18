// /static/index.js
console.log('Starting DocFinder')

var prevfile = "";
var test;
var dclick_e = null;
var viewtype = 'default';

function init(e) {
    console.log("running init()");

    $('a#expand').click(function(e) {
         console.log("expanding");
         $('#tree1').tree({
            autoOpen: 2,
            data: docs
        });
        $('#tree1').tree('openNode', $("#tree1").tree('getNodeById', 1), false);
    });

    var docs = [        // stub for testing
//        { name: 'Account #1',
//            children: [
//                { name: 'New Folder',
//                  children: [
//                    { name: 'File 1.1' },
//                    { name: 'File 1.2' },
//                    { name: 'Folder 1.1',
//                    children: [
//                        { name: 'File 1.1.1' },
//                        { name: 'File 1.1.2' }
//                    ]}
//                ]}
//            ]
//        },
//        { name: 'Account #2',
//            children: [
//                { name: 'File 2.1' }
//            ]
//        },
//        { name: 'Account 3.0' }
    ];
    make_tree(docs);
    load_docs();
 }

function make_tree(docs) {
    $('#tree1').tree({
    data: docs,
    slide: true,
    autoOpen: 1,
    onCreateLi: function(node, $li, is_selected) {
        // Add 'icon' span before title
        var $title = $li.find('.jqtree-title');
        if (node.getLevel() == 1) {         // This is the account icon
            $title.prepend(' ');
            $title.prepend(
                $('<i class="fa fa-id-card" aria-hidden="false"></span>'));
        }
        else if (node.getLevel() == 2) {         // This is the Source icon
            $title.prepend(' ');
            $title.prepend(
                $('<i class="fa fa-database aria-hidden="false"></span>'));
        }
        else if (node.children.length != 0) {   // is it a folder then
            $title.prepend(' ');
            $title.prepend(
                $('<i class="fa fa-fw fa-folder" ></span>'))
        }
        else {
            $title.prepend(' ');
            $title.prepend(
                $('<i class="fa fa-fw fa-folder"></span>'))     // Not showing files in Navigator
        }
        }
    })

}


function load_docs(e) {
    console.log("/finder_view")
    $.getJSON('/finder/view/', {viewtype: '"' + viewtype + '"'}, function(data) {
        console.log("/finder_view Result " + viewtype);
        i = 1;
        $('#tree1').tree('destroy');
        make_tree();

        // loop through results and append elements to the tree
        parentNode = null;
        this_acct = 0;
        this_source = 0;
        this_parent = 0;
        this_doc = 0;
        this_acct_nm = "";
        this_source_nm = "";
        this_parent_nm = "";
        this_doc_nm = "";
        console.log(data);
        console.log(data[0]);

        for (row of data) {
//            console.log(i, row);

            if (row.acct.name != this_acct_nm) {
                // Add New Acct
                parentNode = null;
                $("#tree1").tree('appendNode',
                { name:   row.acct.name,
                  id:     i
                },
                parentNode);
                parentNode = $("#tree1").tree('getNodeById', i);
                i += 1;
                this_acct = parentNode.id;
                this_acct_nm = parentNode.name;

                // Add new Source
                $("#tree1").tree('appendNode',
                { name:   row.source.name,
                  id:     i
                },
                parentNode);
                parentNode = $("#tree1").tree('getNodeById', i);
                i += 1;
                this_source = parentNode.id;
                this_source_nm = parentNode.name;

                //Add New Parent
                $("#tree1").tree('appendNode',
                { name:   row.parent.name,
                  id:     i
                },
                parentNode);
                parentNode = $("#tree1").tree('getNodeById', i);
                i += 1;
                this_parent = parentNode.id;
                this_parent_nm = parentNode.name;
            }
            else if (row.source.name != this_source_nm) {
                // Add new Source
                parentNode = $("#tree1").tree('getNodeById', this_acct);
                $("#tree1").tree('appendNode',
                { name:   row.source.name,
                  id:     i
                },
                parentNode);
                parentNode = $("#tree1").tree('getNodeById', i);
                i += 1;
                this_source = parentNode.id;
                this_source_nm = parentNode.name;

                //Add New Parent
                $("#tree1").tree('appendNode',
                { name:   row.parent.name,
                  id:     i
                },
                parentNode);
                parentNode = $("#tree1").tree('getNodeById', i);
                i += 1;
                this_parent = parentNode.id;
                this_parent_nm = parentNode.name;
            }
            else if (row.parent.name != this_parent_nm) {
                //Add New Parent
                parentNode = $("#tree1").tree('getNodeById', this_source);
                $("#tree1").tree('appendNode',
                { name:   row.parent.name,
                  id:     i
                },
                parentNode);
                parentNode = $("#tree1").tree('getNodeById', i);
                i += 1;
                this_parent = parentNode.id;
                this_parent_nm = parentNode.name;
            }
            // parent levels are the same or just added - now add the document to the doc list
//            $("#tree1").tree('appendNode',
//            { name:   row.doc.name,
//              id:     row.doc.id
//            },
//            parentNode);
//            i += 1;
            this_doc = parentNode.id;
            this_doc_nm = parentNode.name;

            $('#doctable').append('<tr><td scope="row" width="100px">' + row.acct.name
            + '</td><td width="100px">' + row.source.name
            + '</td><td width="110px">' + row.parent.name
            + '</td><td width="220px">' + row.doc.name
            + '</td><td width="220px">' + row.doc.last_modified
            + '</td><td width="300px">' + row.doc.mimeType
            + '</td></tr>');

        }
        $('#tree1').tree('openNode', $("#tree1").tree('getNodeById', 1), false);
    })
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

