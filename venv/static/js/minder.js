// /static/index.js
console.log('Starting minder')


function init(e) {
    console.log("running init()");

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
//    make_tree(docs);
//    load_docs();
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

