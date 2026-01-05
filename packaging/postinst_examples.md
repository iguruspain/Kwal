# Ejemplos de scripts postinst / packaging hooks

Este archivo contiene ejemplos de scripts/hooks que los empaquetadores pueden usar
al empaquetar `kwal` para Debian (.deb), RPM y AUR/PKGBUILD. Son plantillas **ejemplares**
— ajústalas según la política de la distribución y revisa los cambios en usuarios existentes.

**Principio de diseño:**
- Los ficheros de plantilla se instalan como parte del paquete en `/usr/share/kwal/templates`.
- Es recomendable copiar (solo) a `/etc/skel/.config/kwal/templates` para que los nuevos usuarios
  reciban las plantillas por defecto, evitando modificar automáticamente los directorios
  personales de usuarios ya existentes sin su consentimiento.

---

## 1) Debian: `debian/postinst` (ejemplo)

```sh
#!/bin/sh -e
# Debhelper / Dpkg maintscript example: debian/postinst

case "$1" in
    configure)
        # If package provides templates under /usr/share/kwal/templates, copy them to /etc/skel
        if [ -d /usr/share/kwal/templates ]; then
            mkdir -p /etc/skel/.config/kwal/templates
            # Copy contents preserving attributes
            cp -a /usr/share/kwal/templates/. /etc/skel/.config/kwal/templates/
            chown -R root:root /etc/skel/.config/kwal/templates
            chmod -R 755 /etc/skel/.config/kwal/templates || true
        fi
        ;;

    abort-upgrade|abort-remove)
        # no-op
        ;;
esac

exit 0
```

Notas:
- Este script se ejecuta como `root`. No copia por defecto a los home de usuarios existentes.
- Si el mantenedor desea copiar a los usuarios existentes, hacerlo con extremo cuidado y
  —preferiblemente— ofrecer una opción opt-in o ejecutar la copia a través de un helper
  ejecutado por cada usuario (p. ej. al primer arranque) para respetar la privacidad.

---

## 2) RPM: `%post` (ejemplo para `*.spec`)

```spec
%post
# Install templates into /etc/skel so new users receive them
if [ -d "%{_datadir}/kwal/templates" ]; then
    install -d /etc/skel/.config/kwal/templates
    cp -a "%{_datadir}/kwal/templates/." /etc/skel/.config/kwal/templates/
    chown -R root:root /etc/skel/.config/kwal/templates
    chmod -R 755 /etc/skel/.config/kwal/templates || true
fi

%postun
# nothing special on uninstall by default
```

Notas:
- `%{_datadir}` suele ser `/usr/share`. Ajusta según macros del spec.

---

## 3) Arch / AUR: `PKGBUILD` (ejemplo `package()`)

```bash
package() {
    # Instala recursos en /usr/share/kwal/templates
    install -d "$pkgdir/usr/share/kwal/templates"
    cp -a "src/resources/templates/." "$pkgdir/usr/share/kwal/templates/"

    # Coloca plantillas por defecto para nuevos usuarios
    install -d "$pkgdir/etc/skel/.config/kwal/templates"
    cp -a "src/resources/templates/." "$pkgdir/etc/skel/.config/kwal/templates/"
    chown -R root:root "$pkgdir/etc/skel/.config/kwal/templates"
    chmod -R 755 "$pkgdir/etc/skel/.config/kwal/templates" || true
}
```

Notas:
- En Arch, `PKGBUILD` construye el árbol de paquete en `$pkgdir`. No modifiques *home* de usuarios
  en tiempo de instalación del paquete.

---

## Recomendaciones para mantenedores
- Prefiere dejar la copia a `~/.config/kwal/templates` en manos del usuario final (por ejemplo
  mediante la opción `--install-templates` incluida en la aplicación o mostrando el diálogo
  de primer arranque). Esto respeta permisos y evita sobrescribir personalizaciones.
- Si decides modificar `/etc/skel`, documenta claramente en las notas del paquete qué hace el
  script postinst y por qué.
- Añade comprobaciones de idempotencia en scripts reales (p. ej. no sobrescribir si las
  versiones coinciden) y trata con cuidado las actualizaciones que cambian plantillas existentes.

---

Si quieres, puedo:
- Convertir alguno de estos ejemplos en scripts concretos bajo `packaging/` (p. ej. `packaging/deb/postinst`).
- Añadir lógica para comprobar versiones y evitar sobrescribir plantillas personalizadas.

