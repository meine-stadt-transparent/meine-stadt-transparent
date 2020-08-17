const path = require('path');
const fs = require('fs');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const {merge} = require('webpack-merge');
const Autoprefixer = require('autoprefixer');
var HardSourceWebpackPlugin = require('hard-source-webpack-plugin');

module.exports = {
    context: path.resolve(__dirname),
    entry: {
        mainapp: '../mainapp/assets/js/index',
        persons: '../mainapp/assets/js/persons',
        calendar: '../mainapp/assets/js/calendar',
        vendor: [
            'jquery',
            'hammerjs/hammer',
            'popper.js',
            'leaflet/src/Leaflet',
            'corejs-typeahead/dist/typeahead.jquery',
        ]
    },
    output: {
        path: path.resolve(__dirname, '../mainapp/assets/bundles/'),
        filename: (process.env.NODE_ENV === 'production' ? '[name]-[hash].js' : '[name].js'),
        pathinfo: false, // https://github.com/webpack/webpack/issues/6767#issuecomment-410899686
    },
    devtool: 'source-map',
    resolveLoader: {
        moduleExtensions: ['-loader']
    },
    module: {
        rules: [{
            test: /\.scss$/,
            use: [MiniCssExtractPlugin.loader, {
                loader: 'css-loader',
                options: {
                    sourceMap: true,
                }
            }, {
                loader: 'resolve-url-loader',
                options: {
                    sourceMap: true
                }
            }, {
                loader: 'postcss-loader',
                options: {
                    plugins: () => [Autoprefixer({})],
                    remove: false,
                    sourceMap: true
                }
            }, {
                loader: 'sass-loader',
                options: {
                    sourceMap: true
                }
            }]
        }, {
            test: /\.js$/,
            exclude: /(node_modules\/bootstrap-daterangepicker\/)/,
            use: {
                loader: 'babel-loader',
                options: {
                    "presets": ["@babel/preset-env"],
                    sourceMap: true
                }
            }
        }, {
            test: /\.(jpe?g|gif|png)$/,
            use: 'file-loader?outputPath=images/&name=[name].[ext]' // adding -[hash] would be better, but seems to lead to problems with default leaflet markers
        }, {
            test: /\.(ttf|otf|eot|svg|woff(2)?)(\?[a-z0-9]+)?$/,
            loader: 'file-loader?name=fonts/[name].[ext]'
        }, {
            test: /\.css$/,
            use: ['style-loader', 'css-loader']
        }
        ]
    },
    resolve: {
        alias: {
            'jquery': path.join(__dirname, '../node_modules/jquery/dist/jquery'),
        }
    },
    plugins: [
        new BundleTracker({
            path: path.resolve(__dirname, '../mainapp/assets/bundles'),
            filename: './webpack-stats.json'
        }),
        new MiniCssExtractPlugin({
            filename: process.env.NODE_ENV === 'production' ? '[name]-[contenthash].css' : '[name].css'
        }),
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            "Hammer": "hammerjs/hammer",
            "Popper": "popper.js",
            "L": "leaflet"
        }),
        new HardSourceWebpackPlugin() // https://github.com/webpack/webpack/issues/6767#issuecomment-410899686
    ],
    mode: process.env.NODE_ENV === 'production' ? 'production' : 'development'
};


let customization_folder = "./customization/";
fs.readdirSync(customization_folder).forEach((dir) => {
    let configFile = customization_folder + dir + '/webpack.config.js';
    if (dir !== 'etc' && fs.existsSync(customization_folder + dir + '/webpack.config.js')) {
        try {
            // Hint: require works relative to the directory of this file (etc/),
            // while fs.readdirSync relative to the project root, therefore this . -> .. trick
            module.exports = merge(module.exports, require('.' + configFile));
            console.log("Using extra configuration: " + configFile);
        } catch (e) {
            console.error('Could not read file: ' + configFile)
        }
    }
});
