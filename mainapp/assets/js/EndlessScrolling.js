/**
 * Endless scrolling for search results
 * https://stackoverflow.com/a/4842226/3549270
 */
export default class EndlessScrolling {
    constructor($button) {
        this.endlessScrollEnded = false;
        this.isLoading = false;
        this.$button = $button;
        this.$target = $("#endless-scroll-target");
        this.$baseUrl = this.$button.data("url");
        this.$button.click(() => {
            this.$button.hide();
            this.checkAndLoad($button);
            this.scrollListener();
        });
    }

    checkAndLoad($button) {
        if (this.isLoading) {
            return;
        }
        if ($(window).scrollTop() >= $(document).height() - $(window).height() - 500) {
            this.isLoading = true;
            //let url = $button.data("url") + "?after=" + (this.$target.find("> li").length - 1);
            let url = this.$baseUrl + "?after=" + this.$target.find("> li").length;
            $.get(url, (data) => {
                let $data = $(data["results"]);
                if ($data.length > 0) {
                    $("#endless-scroll-target").append($data.find("> li"));
                } else {
                    this.endlessScrollEnded = true;
                }
                this.isLoading = false;
            });
        }
    }

    scrollListener() {
        $(window).one("scroll", () => {
            this.checkAndLoad();
            if (!this.endlessScrollEnded) {
                setTimeout(this.scrollListener.bind(this), 100);
            }
        });
    }
}