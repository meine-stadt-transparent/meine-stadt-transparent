const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const ExtractTextPlugin = require("extract-text-webpack-plugin");

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
                    loader: 'sass-loader',
                    options: {
                        sourceMap: (process.env.NODE_ENV !== 'production')
                    }
                }]
            })
        }, {
            test: /\.js$/,
            use: {
                loader: 'babel-loader',
                options: {
                    presets: ["env"],
                    sourceMap: (process.env.NODE_ENV !== 'production')
                }
            }
        }, {
            test: /\.(jpe?g|gif|png)$/,
            use: 'file-loader?emitFile=false&name=[path][name].[ext]'
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
            path: path.resolve(__dirname, '../'),
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
            "Popper": "popper.js"
        }),
        new webpack.optimize.CommonsChunkPlugin('vendor')
    ]
};
