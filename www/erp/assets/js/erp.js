class ERPClass {
    constructor(ioInstance) {
        this.io = ioInstance;
        this.setupSubscriptions();
    }

    setupSubscriptions() {
        // Abonnement aux données ERP
        this.io.subscribe('erp');
        // Écouter les événements liés aux données ERP
        this.io.on('erp', (data, meta) => {
            // Vérifier si les données proviennent du topic 'erp'
            if (meta.topic === 'erp') {
                // Traiter les données ERP reçues
                this.plotErpData(data);
            }
        });
    }

    plotErpMean(erpMeanData) {
        // Extraire les données ERP moyennes (par exemple, temps et amplitude)
        const temps = len(erpMeanData); // Modifier pour correspondre à votre structure de données
        const amplitude = erpMeanData.iloc[0]; // Modifier pour correspondre à votre structure de données

        // Créer les données pour le graphique
        const data = [{
            x: temps,
            y: amplitude,
            type: 'scatter',
            mode: 'lines',
            name: 'ERP moyen'
        }];

        // Définir les options de la disposition
        const layout = {
            title: 'ERP moyen',
            xaxis: { title: 'Temps (ms)' },
            yaxis: { title: 'Amplitude' }
        };

        // Tracer le graphique à l'intérieur du conteneur 'erp-plot'
        Plotly.newPlot('erp-plot', data, layout);
    }
}

// Exemple d'utilisation :
async settings => {
    let ioInstance = new IO(); // Remplacez par votre instance IO
    let erpClass = new ERPClass(ioInstance);
};