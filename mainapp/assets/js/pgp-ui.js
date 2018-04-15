/**
 * UI for selecting a PGP key from a sks keyserver, inspired by selbstauskunft.net
 */
export default class PgpUi {
    constructor($input) {
        this.$form = $("#pgp-form");

        let server_base = this.$form.data("sks-keyserver");
        this.url_template_search = "https://" + server_base + "/pks/lookup?options=mr&search=";
        this.url_template_get = "https://" + server_base + "/pks/lookup?op=get&options=mr&search=0x";
        this.mail = this.$form.data("pgp-input");
        this.$key_list = $input.find(".pgp-select > div");
        this.$dropdown_button = $input.find(".pgp-select > button");
        this.$dropdown_button.on("click", this.onInitialSelect.bind(this))
    }

    onInitialSelect() {
        this.$dropdown_button.off("click");

        let url = this.url_template_search + encodeURIComponent(this.mail);

        fetch(url)
            .then((data) => {
                return data.text();
            })
            .then(this.dataToOption.bind(this));
    }

    dataToOption(text) {
        // Get rid of the placeholder
        this.$key_list.empty();

        let keys = [];
        let lines = text.trim().split("\n");
        let version = lines[0].trim();
        if (version !== "info:1:2" && version !== "info:1:3") {
            console.warn("Keyserver reported an incorrect api version: '" + version + "'");
            this.$key_list.append("<p class=\"dropdown-item\">There was an Error searching for the pgp keys</p>");
        }

        for (let i = 1; i < lines.length; i++) {
            let split = lines[i].split(":");
            if (split[0] === "pub") {
                keys.push({"fingerprint": split[1], "identity": null, "timestamp": new Date(split[4] * 1000)})
            } else if (split[0] === "uid") {
                if (!keys[keys.length - 1]["identity"]) {
                    keys[keys.length - 1]["identity"] = split[1];
                }
            }
        }

        keys.forEach(this.addKeyToList.bind(this));
    }

    addKeyToList(key) {
        let option = $("<a class=\"dropdown-item\" href=\"#\"></a>");
        let p1 = $("<div></div>");
        let p2 = $("<div></div>");
        p1.text(decodeURIComponent(key["identity"]));
        p2.text(key["fingerprint"]);

        option.append(p1);
        option.append(p2);

        option.on("click", this.onKeySelected.bind(this, key["fingerprint"]));

        this.$key_list.append(option);
    }

    onKeySelected(fingerprint) {
        let url = this.url_template_get + fingerprint;
        fetch(url)
            .then((data) => {
                return data.text();
            })
            .then((text) => {
                $("<input>")
                    .attr("type", "hidden")
                    .attr("name", "pgp_key")
                    .val(text)
                    .appendTo(this.$form);
                $("<input>")
                    .attr("type", "hidden")
                    .attr("name", "pgp_key_fingerprint")
                    .val(fingerprint).appendTo(this.$form);

                this.$form.submit();
            });
    }
}
