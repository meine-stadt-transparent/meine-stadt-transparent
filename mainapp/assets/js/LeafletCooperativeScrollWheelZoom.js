import L from "leaflet";
import {ScrollWheelZoom} from "leaflet/src/map/handler/Map.ScrollWheelZoom";
import {TextHint} from "./LeafletTextHint";

export let CooperativeScrollWheelZoom = ScrollWheelZoom.extend({
    initialize: function (map) {
        this._map = map;
        this._textmarker = new TextHint({
            position: 'topright',
            text: 'Inactive - click to activate',
            cssClass: 'leaflet-control-attribution map-incative-hint'
        });
    },

    addHooks: function () {
        L.DomEvent.on(this._map._container, 'mousewheel', this._onWheelScroll, this);

        this._delta = 0;
    },

    removeHooks: function () {
        L.DomEvent.off(this._map._container, 'mousewheel', this._onWheelScroll, this);
    },

    _onWheelScroll: function (e) {
        // Scroll wheel is only enabled if the map is active
        if (this._map.getContainer() !== document.activeElement) {
            return;
        }

        ScrollWheelZoom.prototype._onWheelScroll.call(this, e);
    }
});
