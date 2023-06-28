=============
kanod-greeter
=============
Adds configuration so that the end-user can modify the message displayed
when logging on an Ubuntu system.

The ``greeting`` element added in configuration is viewable both on console
logging and over ssh (after Ubuntu standard banner).

The static element modifies the behaviour of ``motd`` used for ssh loggings.
News can be removed with the image build flag ``no-motd-news`` that set
`diskimage-builder` variable ``${DIB_NO_MOTD_NEWS}``.