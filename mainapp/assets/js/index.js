import style from '../css/mainapp.scss';
import IndexView from "./IndexView";

window.jQuery = require('jquery');

//require('materialize-css/dist/js/materialize.js');

require('materialize-css/js/initial.js');
require('materialize-css/js/jquery.easing.1.4.js');
require('materialize-css/js/animation.js');
require('materialize-css/js/velocity.min.js');
require('materialize-css/js/hammer.min.js');
require('materialize-css/js/jquery.hammer.js');
require('materialize-css/js/global.js');
//require('materialize-css/js/collapsible.js');
//require('materialize-css/js/dropdown.js');
require('materialize-css/js/modal.js');
//require('materialize-css/js/materialbox.js');
//equire('materialize-css/js/parallax.js');
//require('materialize-css/js/tabs.js');
//require('materialize-css/js/tooltip.js');
//require('materialize-css/js/waves.js');
//require('materialize-css/js/toasts.js');
require('materialize-css/js/sideNav.js');
//require('materialize-css/js/scrollspy.js');
require('materialize-css/js/forms.js');
//require('materialize-css/js/slider.js');
//require('materialize-css/js/cards.js');
//require('materialize-css/js/chips.js');
//require('materialize-css/js/pushpin.js');
require('materialize-css/js/buttons.js');
//require('materialize-css/js/transitions.js');
//require('materialize-css/js/scrollFire.js');
//require('materialize-css/js/date_picker/picker.js');
//require('materialize-css/js/date_picker/picker.date.js');
//require('materialize-css/js/date_picker/picker.time.js');
//require('materialize-css/js/character_counter.js');
//require('materialize-css/js/carousel.js');
require('materialize-css/js/tapTarget.js');


new IndexView();

$(function() {
    console.log("Hello 🌍");

    $('.modal').modal();
    $('.button-collapse').sideNav({
      menuWidth: 300, // Default is 300
      edge: 'left', // Choose the horizontal origin
      closeOnClick: true, // Closes side-nav on <a> clicks, useful for Angular/Meteor
      draggable: true, // Choose whether you can drag to open on touch screens,
    }
  );
});
