odoo.define('custom_powerbi_connector.pfe_viewer', function (require) {
    'use strict';

    var AbstractField = require('web.AbstractField');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;

    var PfeViewer = AbstractField.extend({
        template: 'PfeViewer',
        supportedFieldTypes: ['binary'],

        // Initialisation du widget
        init: function () {
            this._super.apply(this, arguments);
        },

        // Lors de la mise à jour du champ, charger le PDF
        _render: function () {
            if (this.value) {
                // Créez l'URL du fichier PDF à partir de la valeur binaire
                var pdfUrl = 'data:application/pdf;base64,' + this.value;

                // Utilisez PDF.js pour afficher le PDF
                var viewerContainer = this.$el[0];
                var pdfjsLib = window['pdfjs-dist/build/pdf'];
                pdfjsLib.GlobalWorkerOptions.workerSrc = '//cdnjs.cloudflare.com/ajax/libs/pdf.js/2.5.207/pdf.worker.min.js';

                pdfjsLib.getDocument(pdfUrl).promise.then((pdfDoc) => {
                    var pageNum = 1;
                    pdfDoc.getPage(pageNum).then(function(page) {
                        var scale = 1.5;
                        var viewport = page.getViewport({ scale: scale });
                        var canvas = document.createElement('canvas');
                        var context = canvas.getContext('2d');
                        canvas.height = viewport.height;
                        canvas.width = viewport.width;
                        viewerContainer.appendChild(canvas);

                        var renderContext = {
                            canvasContext: context,
                            viewport: viewport
                        };
                        page.render(renderContext);
                    });
                });
            } else {
                this.$el.html('<p>' + _t('No PDF available') + '</p>');
            }
        }
    });

    // Enregistrer le widget
    core.form_widget_registry.add('pfe_viewer', PfeViewer);

    return PfeViewer;
});
