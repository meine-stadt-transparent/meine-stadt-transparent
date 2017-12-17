const moment = require('moment');

export default class FacettedSearchDateRange {
    constructor($facet) {
        this.$facet = $facet;

        this.$inputAfter = this.$facet.find("input[name=after]");
        this.$inputBefore = this.$facet.find("input[name=before]");

        this.$openerBtn = $facet.find('#timeRangeButton');
        let strings = this.$openerBtn.data("strings");
        this.buildDateRanges(strings);
        this.setDateRangeStr();

        this.$openerBtn.daterangepicker(this.getDateRangePickerOptions(strings), this.onDatePickerChanged.bind(this));

        this.$openerBtn.on('cancel.daterangepicker', this.onDatePickerCanceled.bind(this));

        // Workaround to create a "toggling" behavior
        let closeOnClick = () => {
            $(document).trigger("mousedown.daterangepicker");
        };
        this.$openerBtn.on("show.daterangepicker", () => {
            // Wait until the current click event is safely gone
            window.setTimeout(() => {
                this.$openerBtn.on("click", closeOnClick);
            }, 500);
        });
        this.$openerBtn.on("hide.daterangepicker", () => {
            this.$openerBtn.off("click", closeOnClick);
        });
    }

    getDateRangePickerOptions(strings) {
        return {
            locale: {
                format: 'YYYY-MM-DD',
                applyLabel: strings['apply'],
                cancelLabel: strings['na'],
                customRangeLabel: strings['custom'],
                monthNames: strings['month_names'].split('|'),
                daysOfWeek: strings['day_names'].split('|'),
                firstDay: 1
            },
            opens: 'center',
            showDropdowns: true,
            showCustomRangeLabel: true,
            linkedCalendars: false,
            ranges: this.dateRanges,
            applyClass: "btn-primary",
            cancelClass: "btn-danger"
        };
    }

    onDatePickerChanged(start, end) {
        this.$inputBefore.val(end.format("YYYY-MM-DD"));
        this.$inputAfter.val(start.format("YYYY-MM-DD"));
        this.$inputAfter.change();
        this.setDateRangeStr();
    }

    setDateRangeStr() {
        let before = this.$inputBefore.val(),
            after = this.$inputAfter.val(),
            found = false;

        if (after && before) {
            this.$openerBtn.find(".time-not-set").attr("hidden", "hidden");
            this.$openerBtn.find(".time-description").removeAttr("hidden");

            // Find an entry in this.dateRanges whose dates matches the selected values.
            // If an entry is found, the key is the descriptive string to be shown, ...
            Object.keys(this.dateRanges).forEach(dateRange => {
                if (
                    this.dateRanges[dateRange][0].format('YYYY-MM-DD') === after &&
                    this.dateRanges[dateRange][1].format('YYYY-MM-DD') === before
                ) {
                    found = true;
                    this.$openerBtn.find(".time-description").text(dateRange);
                }
            });

            // ...otherwise we just show the explicit date
            if (!found) {
                this.$openerBtn.find(".time-description").text(after + ' - ' + before);
            }
        } else {
            this.$openerBtn.find(".time-not-set").removeAttr("hidden");
            this.$openerBtn.find(".time-description").text("").attr("hidden", "hidden");
        }
    }

    onDatePickerCanceled() {
        this.$inputBefore.val('');
        this.$inputAfter.val('');
        this.$inputAfter.change();
        this.setDateRangeStr();
    }

    buildDateRanges(strings) {
        this.dateRanges = {};
        this.dateRanges[strings['today']] = [moment(), moment()];
        this.dateRanges[strings['last_7d']] = [moment().subtract(6, 'days'), moment()];
        this.dateRanges[strings['this_month']] = [moment().startOf('month'), moment().endOf('month')];
        this.dateRanges[strings['last_month']] = [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')];
        this.dateRanges[strings['this_year']] = [moment().startOf('year'), moment().endOf('year')];
    }

    getQueryString() {
        let str = '';
        if (this.$inputBefore.val() !== '') {
            str += 'after:' + this.$inputAfter.val() + ' ';
        }
        if (this.$inputBefore.val() !== '') {
            str += 'before:' + this.$inputBefore.val() + ' ';
        }
        return str;
    }
}
