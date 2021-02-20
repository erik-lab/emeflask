// /static/index.js
console.log('D!')

var prevfile = 0;

function loadFiles(){
    var li = document.getElementsByTagName("ul");
    for(var i = 0;i<li.length;i++){
        li[i].addEventListener("click", fileClick);}
}

function fileClick(e){
    if (prevfile > 0) {
        document.getElementById(prevfile.toString()).style.backgroundColor = "white";
    }
    document.getElementById(e.target.attributes.id.value.toString()).style.backgroundColor = "lightCyan";
    prevfile = e.target.attributes.id.value;
}
