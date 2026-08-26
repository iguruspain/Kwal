# Maintainer: Your Name <your-email@example.com>
pkgname=kwal-git
pkgver=0.1
pkgrel=1
pkgdesc="Kwal — modern wallpaper manager for KDE Plasma (Kirigami + Python)"
arch=('any')
url="https://github.com/iguruspain/kwal"
license=('GPL3')
groups=('kde-apps')
depends=(
    # System / Qt / KDE
    'python>=3.10'
    'pyside6'
    'qt6-webengine'
    'kirigami'
    # Python-only libraries (from pip / AUR)
    'python-json5'
    'python-materialyoucolor'
    'python-modern-colorthief'
    'python-pillow'
    'python-pywal16'
    'python-tomlkit'
)
makedepends=('git' 'python-build' 'python-installer' 'python-setuptools' 'python-wheel')
optdepends=(
    'matugen: KDE color engine (preferred for wallpaper color extraction)'
    'imagemagick: Advanced image tinting and palette extraction'
    'fastfetch: Terminal fetch tool (tinting target)'
    'starship: Terminal prompt (tinting target)'
    'ulauncher: Application launcher (tinting target)'
)
provides=('kwal')
conflicts=('kwal')
source=("git+https://github.com/iguruspain/kwal.git")
sha256sums=('SKIP')

build() {
    cd "${srcdir}/kwal"
    python -m build --wheel --no-isolation
}

package() {
    cd "${srcdir}/kwal"
    python -m installer --destdir="${pkgdir}" dist/*.whl
}
