/**
 * Metadados de imagem: dimensoes, dispositivo, software e localizacao.
 *
 * Duas mensagens que a tela precisa passar sem que o usuario precise saber de
 * forense:
 *
 * - foto sem EXIF e o caso NORMAL. Toda rede social remove esses dados ao
 *   publicar. Exibir "nenhum metadado" com cara de problema seria enganoso.
 * - GPS e questao de PRIVACIDADE, nao de seguranca. A pessoa raramente sabe
 *   que compartilhou onde mora junto com a foto.
 */

import { Card, DataList, DataRow, Empty } from "@/components/Card";
import type { Gps, ImageAnalysis } from "@/types/analysis";

export function ExifCard({ image }: { image: ImageAnalysis }) {
  if (image.error) {
    return (
      <Card title="Image">
        <p className="text-sm text-amber-600 dark:text-amber-400">{image.error}</p>
      </Card>
    );
  }

  const hasExif = Object.keys(image.exif).length > 0;

  return (
    <div className="flex flex-col gap-4">
      <Card title="Image">
        <DataList>
          <DataRow label="Dimensions">
            {image.width && image.height ? (
              <>
                {image.width} × {image.height} px
                {image.megapixels !== null && (
                  <span className="ml-2 text-muted-foreground">
                    ({image.megapixels} MP)
                  </span>
                )}
              </>
            ) : (
              <Empty>unavailable</Empty>
            )}
          </DataRow>

          <DataRow label="Format">{image.image_format ?? <Empty />}</DataRow>
          <DataRow label="Colour mode">{image.color_mode ?? <Empty />}</DataRow>
        </DataList>
      </Card>

      <Card
        title="EXIF metadata"
        hint="A photo without EXIF is the normal case — social networks strip it on upload."
      >
        {hasExif ? (
          <DataList>
            <DataRow label="Device">
              {image.device_make || image.device_model ? (
                [image.device_make, image.device_model].filter(Boolean).join(" ")
              ) : (
                <Empty />
              )}
            </DataRow>

            <DataRow label="Software">
              {image.software ?? <Empty />}
              {image.software && (
                <span className="ml-2 text-xs text-muted-foreground/60">
                  editing software is information, not a finding
                </span>
              )}
            </DataRow>

            <DataRow label="Recorded at" mono>
              {image.created_at ?? <Empty />}
            </DataRow>
          </DataList>
        ) : (
          <p className="text-sm text-muted-foreground">
            No EXIF metadata. This is not suspicious.
          </p>
        )}
      </Card>

      <LocationCard gps={image.gps} />

      {hasExif && <AllTagsCard exif={image.exif} />}
    </div>
  );
}

function LocationCard({ gps }: { gps: Gps | null }) {
  return (
    <Card
      title="Location"
      hint="Embedded coordinates are a privacy matter, not a security one."
    >
      {gps ? (
        <DataList>
          <DataRow label="Coordinates" mono>
            {gps.latitude}, {gps.longitude}
          </DataRow>
          <DataRow label="Map">
            {/*
              rel="noreferrer" impede que o site de destino receba, pelo
              cabecalho Referer, a informacao de onde o clique veio.
            */}
            <a
              href={`https://www.openstreetmap.org/?mlat=${gps.latitude}&mlon=${gps.longitude}#map=15/${gps.latitude}/${gps.longitude}`}
              target="_blank"
              rel="noreferrer"
              className="text-emerald-600 underline underline-offset-2 dark:text-emerald-400"
            >
              Open in OpenStreetMap
            </a>
          </DataRow>
        </DataList>
      ) : (
        <p className="text-sm text-muted-foreground">
          No GPS coordinates embedded.
        </p>
      )}
    </Card>
  );
}

function AllTagsCard({ exif }: { exif: Record<string, string> }) {
  return (
    <Card title="All EXIF tags">
      <DataList>
        {Object.entries(exif).map(([tag, value]) => (
          <DataRow key={tag} label={tag} mono>
            {value}
          </DataRow>
        ))}
      </DataList>
    </Card>
  );
}
