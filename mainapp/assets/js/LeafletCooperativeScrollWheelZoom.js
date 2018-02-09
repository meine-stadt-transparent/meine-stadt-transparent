import * as L from "leaflet/src/Leaflet";
import {ScrollWheelZoom} from "leaflet/src/map/handler/Map.ScrollWheelZoom";
import {TextHint} from "./LeafletTextHint";

export let CooperativeScrollWheelZoom = ScrollWheelZoom.extend({
	initialize: function (map) {
		this._inactivehint = false; //  @TODO Decide if this hint is actually helpful or not
		this._map = map;
		this._textmarker = new TextHint({
			position: 'topright',
			text: 'Inactive - click to activate',
			cssClass: 'leaflet-control-attribution map-incative-hint'
		});
	},

	addHooks: function () {
		L.DomEvent.on(this._map._container, 'mousewheel', this._onWheelScroll, this);
		L.DomEvent.on(this._map._container, 'focus', this._onFocus, this);
		L.DomEvent.on(this._map._container, 'blur', this._onBlur, this);

		this._delta = 0;

		if (this._inactivehint) {
            this._textmarker.addTo(this._map);
        }
	},

	removeHooks: function () {
		L.DomEvent.off(this._map._container, 'mousewheel', this._onWheelScroll, this);
		L.DomEvent.off(this._map._container, 'focus', this._onFocus, this);
		L.DomEvent.off(this._map._container, 'blur', this._onBlur, this);

		if (this._inactivehint) {
            this._textmarker.remove();
        }
	},

	_onWheelScroll: function (e) {
		// Scroll wheel is only enabled if the map is active
        if (this._map.getContainer() !== document.activeElement) {
        	return;
		}

		ScrollWheelZoom.prototype._onWheelScroll.call(this, e);
    },

    _onFocus: function () {
		if (this._inactivehint) {
            this._textmarker.remove();
        }
    },

    _onBlur: function () {
		if (this._inactivehint) {
            this._textmarker.addTo(this._map);
        }
    },
});
