import * as L from "leaflet/src/Leaflet";

L.Control.TextHint = L.Control.extend({
    options: {
        position: 'bottomleft',
        text: ''
    },
    onAdd: function (map) {
        let div = L.DomUtil.create('div', 'leaflet-control-attribution');
        div.textContent = this.options.text;
        return div;
    },

    onRemove: function (map) {
        // Nothing to do here
    }
});

export var TextHint = L.Control.TextHint;