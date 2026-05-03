<!-- CABECERA DE REPORTE CORREGIDA -->
<div id="report-header-ui" class="report-header">
    <!-- Logo Tandanor corregido -->
    <img src="https://raw.githubusercontent.com/juangautobr2-bit/ordoklartandanor/main/TANDANOR.PNG" crossorigin="anonymous">
    
    <div class="report-title">
        <h1 id="rt-titulo">INFORME DE SERVICIO</h1>
        <p id="rt-subtitulo">SUBTÍTULO</p>
    </div>
    
    <!-- Logo Watchman corregido -->
    <img src="https://raw.githubusercontent.com/juangautobr2-bit/ordoklartandanor/main/WATCHMAN.SVG" crossorigin="anonymous">
</div>

<script>
// Ajuste en la función de generación de PDF para que acepte las imágenes externas
function generatePDF(titulo, subtitulo, filename, orientation) {
    document.getElementById('rt-titulo').innerText = titulo;
    document.getElementById('rt-subtitulo').innerText = subtitulo;
    document.getElementById('report-header-ui').style.display = 'flex';
    
    const element = document.body;
    const opt = {
        margin: 5,
        filename: filename,
        image: { type: 'jpeg', quality: 0.98 },
        // IMPORTANTE: useCORS permite que html2canvas cargue los logos de GitHub
        html2canvas: { 
            scale: 2, 
            useCORS: true, 
            logging: true, 
            letterRendering: true 
        },
        jsPDF: { unit: 'mm', format: orientation == 'landscape' ? 'a3' : 'a4', orientation: orientation }
    };

    html2pdf().set(opt).from(element).save().then(() => {
        document.getElementById('report-header-ui').style.display = 'none';
    });
}
</script>
