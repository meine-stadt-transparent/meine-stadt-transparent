const path = require('path');
const fs = require('fs');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const ExtractTextPlugin = require("extract-text-webpack-plugin");
const merge = require('webpack-merge');
const Autoprefixer = require('autoprefixer');

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
            'bootstrap/dist/js/bootstrap.js',
            'corejs-typeahead/dist/typeahead.jquery',
            'bootstrap-daterangepicker/daterangepicker'
        ]
    },
    output: {
        path: path.resolve(__dirname, '../mainapp/assets/bundles/'),
        filename: (process.env.NODE_ENV === 'production' ? '[name]-[hash].js' : '[name].js')
    },
    devtool: (process.env.NODE_ENV !== 'production' ? 'source-map' : false),
    resolveLoader: {
        moduleExtensions: ['-loader']
    },
    module: {
        rules: [{
            test: /\.scss$/,
            use: ExtractTextPlugin.extract({
                fallback: 'style-loader',
                //resolve-url-loader may be chained before sass-loader if necessary
                use: [{
                    loader: 'css-loader',
                    options: {
                        sourceMap: (process.env.NODE_ENV !== 'production'),
                        minimize: true
                    }
                }, {
                    loader: 'resolve-url-loader',
                    options: {
                        sourceMap: (process.env.NODE_ENV !== 'production')
                    }
                }, {
                    loader: 'postcss-loader',
                    options: {
                        plugins: () => [Autoprefixer({browsers: ["defaults"]})],
                        remove: false,
                        sourceMap: true
                    }
                }, {
                    loader: 'sass-loader',
                    options: {
                        sourceMap: (process.env.NODE_ENV !== 'production')
                    }
                }]
            })
        }, {
            test: /\.js$/,
            exclude: /(node_modules\/bootstrap\-daterangepicker\/)/,
            use: {
                loader: 'babel-loader',
                options: {
                    presets: ["env"],
                    sourceMap: (process.env.NODE_ENV !== 'production')
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
        new ExtractTextPlugin({
            filename: process.env.NODE_ENV === 'production' ? '[name]-[contenthash].css' : '[name].css',
            allChunks: true
        }),
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            "Hammer": "hammerjs/hammer",
            "Popper": "popper.js",
            "L": "leaflet"
        }),
        new webpack.optimize.CommonsChunkPlugin('vendor')
    ]
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
