"""apps/common/exports.py — Utilitaire pour exports CSV en streaming."""

import csv
from django.http import StreamingHttpResponse


class _EchoBuffer:
    """Pseudo-buffer : retourne la valeur dès qu'elle est écrite (pas de mise en mémoire)."""
    def write(self, value):
        return value


def stream_csv_response(row_generator, filename):
    """
    Crée une StreamingHttpResponse CSV depuis un générateur de lignes.

    Chaque élément du générateur doit être une liste de valeurs.
    Les lignes sont envoyées au navigateur au fur et à mesure — aucun timeout
    même sur des milliers de lignes.

    Usage :
        def mes_lignes():
            yield ['Col1', 'Col2']
            for obj in qs.iterator(chunk_size=200):
                yield [obj.champ1, obj.champ2]

        return stream_csv_response(mes_lignes(), 'export.csv')
    """
    buf = _EchoBuffer()
    writer = csv.writer(buf, delimiter=';')
    response = StreamingHttpResponse(
        (writer.writerow(row) for row in row_generator),
        content_type='text/csv; charset=utf-8-sig',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
