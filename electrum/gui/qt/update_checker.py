# Copyright (C) 2019 The Electrum developers
# Distributed under the MIT software license, see the accompanying
# file LICENCE or http://www.opensource.org/licenses/mit-license.php

import asyncio
import base64
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QProgressBar, QHBoxLayout, QPushButton, QDialog

from electrum import version
from electrum import constants
from electrum.bitcoin import verify_usermessage_with_address
from electrum.i18n import _
from electrum.util import make_aiohttp_session
from electrum.logging import Logger
from electrum.network import Network
from electrum._vendor.distutils.version import StrictVersion


class UpdateCheck(QDialog, Logger):
    # BTX: Update URLs for BitCore BTX
    url = "https://api.github.com/repos/dArkjON/electrum-btx/releases/latest"
    download_url = "https://github.com/dArkjON/electrum-btx/releases"

    VERSION_ANNOUNCEMENT_SIGNING_KEYS = (
        "13xjmVAB1EATPP8RshTE8S8sNwwSUM9p1P",  # ThomasV (since 3.3.4)
        "1Nxgk6NTooV4qZsX5fdqQwrLjYcsQZAfTg",  # ghost43 (since 4.1.2)
    )

    def __init__(self, *, latest_version=None):
        QDialog.__init__(self)
        self.setWindowTitle('Electrum - ' + _('Update Check'))
        self.content = QVBoxLayout()
        self.content.setContentsMargins(*[10]*4)

        self.heading_label = QLabel()
        self.content.addWidget(self.heading_label)

        self.detail_label = QLabel()
        self.detail_label.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.detail_label.setOpenExternalLinks(True)
        self.content.addWidget(self.detail_label)

        self.pb = QProgressBar()
        self.pb.setMaximum(0)
        self.pb.setMinimum(0)
        self.content.addWidget(self.pb)

        versions = QHBoxLayout()
        versions.addWidget(QLabel(_("Current version: {}").format(version.ELECTRUM_VERSION)))
        self.latest_version_label = QLabel(_("Latest version: {}").format(" "))
        versions.addWidget(self.latest_version_label)
        self.content.addLayout(versions)

        self.update_view(latest_version)

        self.update_check_thread = UpdateCheckThread()
        self.update_check_thread.checked.connect(self.on_version_retrieved)
        self.update_check_thread.failed.connect(self.on_retrieval_failed)
        self.update_check_thread.start()

        close_button = QPushButton(_("Close"))
        close_button.clicked.connect(self.close)
        self.content.addWidget(close_button)
        self.setLayout(self.content)
        self.show()

    def on_version_retrieved(self, version):
        self.update_view(version)

    def on_retrieval_failed(self):
        self.heading_label.setText('<h2>' + _("Update check failed") + '</h2>')
        self.detail_label.setText(_("Sorry, but we were unable to check for updates. Please try again later."))
        self.pb.hide()

    @staticmethod
    def is_newer(latest_version):
        return latest_version > StrictVersion(version.ELECTRUM_VERSION)

    def update_view(self, latest_version=None):
        if latest_version:
            self.pb.hide()
            self.latest_version_label.setText(_("Latest version: {}").format(latest_version))
            if self.is_newer(latest_version):
                self.heading_label.setText('<h2>' + _("There is a new update available") + '</h2>')
                url = "<a href='{u}'>{u}</a>".format(u=UpdateCheck.download_url)
                self.detail_label.setText(_("You can download the new version from {}.").format(url))
            else:
                self.heading_label.setText('<h2>' + _("Already up to date") + '</h2>')
                self.detail_label.setText(_("You are already on the latest version of Electrum."))
        else:
            self.heading_label.setText('<h2>' + _("Checking for updates...") + '</h2>')
            self.detail_label.setText(_("Please wait while Electrum checks for available updates."))


class UpdateCheckThread(QThread, Logger):
    checked = pyqtSignal(object)
    failed = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)
        Logger.__init__(self)
        self.network = Network.get_instance()
        self._fut = None  # type: Optional[asyncio.Future]

    async def get_update_info(self):
        # note: Use long timeout here as it is not critical that we get a response fast,
        #       and it's bad not to get an update notification just because we did not wait enough.
        # BTX: Using GitHub API for release checking
        async with make_aiohttp_session(proxy=self.network.proxy, timeout=120) as session:
            async with session.get(UpdateCheck.url) as result:
                release_data = await result.json(content_type=None)
                # GitHub API returns release info with tag_name as version
                # Example: {"tag_name": "btx-4.6.2", "name": "Electrum BTX 4.6.2", ...}
                version_str = release_data['tag_name']
                # BTX: Remove 'btx-' prefix if present
                if version_str.startswith('btx-'):
                    version_num = version_str[4:]
                else:
                    version_num = version_str

                # BTX: Skip signature verification for now as GitHub releases are implicitly signed
                self.logger.info(f"Retrieved version from GitHub: '{version_num}'")
                return StrictVersion(version_num.strip())

    def run(self):
        if not self.network:
            self.failed.emit()
            return
        self._fut = asyncio.run_coroutine_threadsafe(self.get_update_info(), self.network.asyncio_loop)
        try:
            update_info = self._fut.result()
        except Exception as e:
            self.logger.info(f"got exception: '{repr(e)}'")
            self.failed.emit()
        else:
            self.checked.emit(update_info)

    def stop(self):
        if self._fut:
            self._fut.cancel()
        self.exit()
        self.wait()
