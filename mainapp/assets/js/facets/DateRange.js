const moment = require('moment');

export default class FacetDateRange {
    constructor($facet) {
        this.$facet = $facet;

        this.$inputAfter = this.$facet.find("input[name=after]");
        this.$inputBefore = this.$facet.find("input[name=before]");
        this.$template = this.$facet.find(".daterangepicker-template").removeClass("daterangepicker-template").remove();

        this.$openerBtn = $facet.find('#timeRangeButton');
        let strings = this.$openerBtn.data("strings");
        this.buildDateRanges(strings);
        this.setDateRangeStr();

        let options = this.getDateRangePickerOptions(strings, this.$inputAfter.val(), this.$inputBefore.val());
        this.$openerBtn.daterangepicker(options, this.onDatePickerChanged.bind(this));

        this.$openerBtn.on('cancel.daterangepicker', this.onDatePickerCanceled.bind(this));
    }

    getDateRangePickerOptions(strings, start, end) {
        let options = {
            locale: {
                format: 'YYYY-MM-DD',
                applyLabel: strings['apply'],
                cancelLabel: this.$template.find(".remove-filter").html(),
                customRangeLabel: strings['custom'],
                monthNames: strings['month_names'].split('|'),
                daysOfWeek: strings['day_names'].split('|'),
                firstDay: 1
            },
            opens: 'center',
            showDropdowns: true,
            showCustomRangeLabel: true,
            linkedCalendars: false,
            alwaysToggle: true,
            ranges: this.dateRanges,
            applyClass: "",
            cancelClass: "",
            template: this.$template
        };
        if (start) {
            options['startDate'] = start;
        }
        if (end) {
            options['endDate'] = end;
        }
        return options;
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
        this.$inputBefore.change();
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
        if (this.$inputAfter.val() !== '') {
            str += 'after:' + this.$inputAfter.val() + ' ';
        }
        if (this.$inputBefore.val() !== '') {
            str += 'before:' + this.$inputBefore.val() + ' ';
        }
        return str;
    }

    setFromQueryString(params) {
        if (params['before']) {
            this.$inputBefore.val(params['before']);
            this.$openerBtn.data('daterangepicker').setEndDate(this.$inputBefore.val());
        } else {
            this.$inputBefore.val('');
            // Setting enddate to null in the daterangepicker somehow leads to a broken interface, so we don't do it
        }
        if (params['after']) {
            this.$inputAfter.val(params['after']);
            this.$openerBtn.data('daterangepicker').setStartDate(this.$inputAfter.val());
        } else {
            this.$inputAfter.val('');
            // Setting startdate to null in the daterangepicker somehow leads to a broken interface, so we don't do it
        }
        this.setDateRangeStr();
    }
}
