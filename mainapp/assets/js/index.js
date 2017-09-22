import style from '../css/mainapp.scss';
import HomeMap from "./HomeMap";

console.log("1");
window.jQuery = require('jquery');
console.log("2");
require('popper.js/dist/popper.js');
require('bootstrap/dist/js/bootstrap.js');
console.log("3");

$(function() {
    console.log("Hello 🌍");
    /*
    $('.modal').modal();
    $('.button-collapse').sideNav({
      menuWidth: 300, // Default is 300
      edge: 'left', // Choose the horizontal origin
      closeOnClick: true, // Closes side-nav on <a> clicks, useful for Angular/Meteor
      draggable: true, // Choose whether you can drag to open on touch screens,
    }
  );
  */

    $(".js-home-map").each(function() {
        new HomeMap($(this));
    });
});
