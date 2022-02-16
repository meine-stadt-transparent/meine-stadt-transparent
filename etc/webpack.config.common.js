const path = require('path');
const fs = require('fs');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const {merge} = require('webpack-merge');

module.exports = {
    context: path.resolve(__dirname),
    entry: {
        mainapp: '../mainapp/assets/js/index',
        persons: '../mainapp/assets/js/persons',
        calendar: '../mainapp/assets/js/calendar',
    },
    output: {
        path: path.resolve(__dirname, '../mainapp/assets/bundles/'),
        filename: (process.env.NODE_ENV === 'production' ? '[name]-[hash].js' : '[name].js'),
        publicPath: '',
    },
    devtool: 'source-map',
    module: {
        rules: [{
            test: /\.scss$/,
            use: [
                MiniCssExtractPlugin.loader, {
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
                        postcssOptions: {
                            plugins: [
                                [
                                    'autoprefixer',
                                    {},
                                ],
                            ],
                        },
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
                    presets: ['@babel/preset-env'],
                    sourceMap: true
                }
            }
        }, {
            test: /\.(jpe?g|gif|png)$/,
            type: 'asset/resource',
            generator: {
                outputPath: 'images',
                filename: '[name][ext]'
            }
        }, {
            test: /\.(woff(2)?|otf|ttf|eot|svg)(\?v=\d+\.\d+\.\d+)?$/,
            type: 'asset/resource',
            generator: {
                filename: '[name][ext]'
            }
        }, {
            test: /\.css$/,
            use: ['style-loader', 'css-loader']
        }]
    },
    resolve: {
        alias: {
            'jquery': path.join(__dirname, '../node_modules/jquery/dist/jquery'),
        }
    },
    plugins: [
        new BundleTracker({
            filename: path.resolve(__dirname, '../mainapp/assets/bundles/webpack-stats.json')
        }),
        new MiniCssExtractPlugin({
            filename: process.env.NODE_ENV === 'production' ? '[name]-[contenthash].css' : '[name].css'
        }),
        new webpack.ProvidePlugin({
            $: 'jquery',
            jQuery: 'jquery',
            Hammer: 'hammerjs/hammer',
            Popper: '@popper/core',
            L: 'leaflet'
        }),
    ],
    optimization: {
        splitChunks: {
            cacheGroups: {
                vendor: {
                    test: /[\\/]node_modules[\\/]/,
                    name: 'vendor',
                    chunks: 'all',
                },
            },
        },
    },
    mode: process.env.NODE_ENV === 'production' ? 'production' : 'development'
};


let customization_folder = './customization/';
fs.readdirSync(customization_folder).forEach((dir) => {
    let configFile = customization_folder + dir + '/webpack.config.js';
    if (dir !== 'etc' && fs.existsSync(customization_folder + dir + '/webpack.config.js')) {
        try {
            // Hint: require works relative to the directory of this file (etc/),
            // while fs.readdirSync relative to the project root, therefore this . -> .. trick
            module.exports = merge(module.exports, require('.' + configFile));
            console.log('Using extra configuration: ' + configFile);
        } catch (e) {
            console.error('Could not read file: ' + configFile)
        }
    }
});
