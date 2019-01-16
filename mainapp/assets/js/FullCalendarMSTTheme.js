// Adapted from StandardTheme
export class FullCalendarMSTTheme {
    constructor(optionsManager) {
        this.optionsManager = optionsManager;
        this.setIconOverride(
            this.optionsManager.get("buttonIcons")
        );

        this.classes = {
            widget: 'fc-unthemed',
            widgetHeader: 'fc-widget-header',
            widgetContent: 'fc-widget-content',

            buttonGroup: 'btn-group',
            button: 'btn btn-content-switcher',
            cornerLeft: 'fc-corner-left',
            cornerRight: 'fc-corner-right',
            stateDefault: '',
            stateActive: 'active',
            stateDisabled: 'disabled',
            stateHover: '',
            stateDown: 'fc-state-down',

            popoverHeader: 'fc-widget-header',
            popoverContent: 'fc-widget-content',

            // day grid
            headerRow: 'fc-widget-header',
            dayRow: 'fc-widget-content',

            // list view
            listView: 'fc-widget-content'
        };

        this.iconClasses = {
            close: 'fc-icon-x',
            prev: 'fc-icon-left-single-arrow',
            next: 'fc-icon-right-single-arrow',
            prevYear: 'fc-icon-left-double-arrow',
            nextYear: 'fc-icon-right-double-arrow'
        };
    }

    setIconOverride(iconOverrideHash) {
        let iconClassesCopy;
        let buttonName;

        if ($.isPlainObject(iconOverrideHash)) {
            iconClassesCopy = $.extend({}, this.iconClasses);

            for (buttonName in iconOverrideHash) {
                iconClassesCopy[buttonName] = this.applyIconOverridePrefix(
                    iconOverrideHash[buttonName]
                )
            }

            this.iconClasses = iconClassesCopy
        } else if (iconOverrideHash === false) {
            this.iconClasses = {}
        }
    }

    applyIconOverridePrefix(className) {
        let prefix = "fc-icon-";

        if (prefix && className.indexOf(prefix) !== 0) { // if not already present
            className = prefix + className
        }

        return className
    }

    getClass(key) {
        return this.classes[key] || ''
    }

    getIconClass(buttonName) {
        let className = this.iconClasses[buttonName];

        if (className) {
            return "fc-icon" + ' ' + className;
        }

        return ''
    }

    getCustomButtonIconClass(customButtonProps) {
        let className = customButtonProps["icon"];

        if (className) {
            return "fc-icon" + ' ' + this.applyIconOverridePrefix(className)
        }

        return ''
    }
}
