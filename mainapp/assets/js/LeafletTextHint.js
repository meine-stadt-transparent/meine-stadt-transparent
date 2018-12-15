import L from "leaflet";

L.Control.TextHint = L.Control.extend({
    options: {
        position: 'bottomleft',
        text: '',
        cssClass: 'leaflet-control-attribution'
    },
    onAdd: function (map) {
        let div = L.DomUtil.create('div', this.options.cssClass);
        div.textContent = this.options.text;
        return div;
    },

    onRemove: function (map) {
        // Nothing to do here
    }
});

export var TextHint = L.Control.TextHint;
