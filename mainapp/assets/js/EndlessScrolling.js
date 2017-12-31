/**
 * Endless scrolling for search results
 * https://stackoverflow.com/a/4842226/3549270
 */
export default class EndlessScrolling {
    loadFurtherHeight = 500;

    constructor($button) {
        this.$button = $button;
        this.reset();
        this.$target = $("#endless-scroll-target");
        this.$button.click(this.activate.bind(this));
    }

    activate() {
        this.$button.hide();
        this.isActive = true;
        this.checkAndLoad();
        this.scrollListener();
    }

    checkAndLoad() {
        if (this.isLoading || !this.isActive) {
            return;
        }

        if ($(window).scrollTop() >= $(document).height() - $(window).height() - this.loadFurtherHeight) {
            this.isLoading = true;
            let url = this.$button.data("url") + "?after=" + this.$target.find("> li").length;
            $.get(url, (data) => {
                let $data = $(data["results"]);
                if ($data.length > 0) {
                    $("#endless-scroll-target").append($data.find("> li"));
                } else {
                    this.isActive = false;
                }
                this.isLoading = false;
            });
        }
    }

    scrollListener() {
        $(window).one("scroll", () => {
            this.checkAndLoad();
            if (this.isActive) {
                setTimeout(this.scrollListener.bind(this), 100);
            }
        });
    }

    // Called from external sources like FacettedSearch.js
    reset() {
        this.isActive = false;
        this.isLoading = false;
        this.$button.show();
    }
}