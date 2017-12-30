// This configuration will be merged into the main webpack configuration.
// Its main purpose is to compile the SCSS-file.
// The file has to be "webpack.config.js", as it will be autodetected by etc/webpack.config.common.js.

module.exports = {
    entry: {
        "mainapp-bedburg": '../bedburg_transparent/assets/js/bedburg-main'
    }
};
