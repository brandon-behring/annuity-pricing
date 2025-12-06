%% quantfin.cls
%% Custom article class for arXiv quantitative finance papers
%% Based on article.cls with enhancements for financial mathematics

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{quantfin}[2025/12/06 Custom QuantFin Article Class]

% Load base article class
\LoadClass[11pt]{article}

% ============================================================================
% Required Packages
% ============================================================================

\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{geometry}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{natbib}
% UTF-8 is default in modern LaTeX; inputenc is not needed
% \usepackage[utf-8]{inputenc}

% ============================================================================
% Page Layout
% ============================================================================

\geometry{
  margin=1in,
  headheight=14pt,
  headsep=0.75in,
  footskip=0.75in
}

% ============================================================================
% Math Macros and Definitions
% ============================================================================

% Expectation operator
\newcommand{\E}{\mathbb{E}}

% Probability measure
\newcommand{\Prob}{\mathbb{P}}

% Risk-neutral measure
\newcommand{\Q}{\mathbb{Q}}

% Real numbers
\newcommand{\R}{\mathbb{R}}

% Natural numbers
\newcommand{\N}{\mathbb{N}}

% Indicator function
\newcommand{\Ind}[1]{\mathbf{1}_{#1}}

% Ceiling and floor
\newcommand{\ceil}[1]{\lceil #1 \rceil}
\newcommand{\floor}[1]{\lfloor #1 \rfloor}

% Variance
\newcommand{\Var}{\text{Var}}

% Covariance
\newcommand{\Cov}{\text{Cov}}

% Standard deviation
\newcommand{\StdDev}{\text{SD}}

% Conditional expectation
\newcommand{\Econd}[2]{\E\left[#1 \mid #2\right]}

% ============================================================================
% Title and Author Formatting
% ============================================================================

\renewcommand\maketitle{\par
  \begingroup
    \renewcommand\thefootnote{\@fnsymbol\c@footnote}%
    \def\@makefnmark{\rlap{\@textsuperscript{\normalfont\@thefnmark}}}%
    \long\def\@makefntext##1{\parindent 1em\noindent
            \hb@xt@1.8em{%
                \hss\@textsuperscript{\normalfont\@thefnmark}}##1}%
    \if@twocolumn
      \ifnum \col@number=\@ne
        \@maketitle
      \else
        \twocolumn[\@maketitle]%
      \fi
    \else
      \newpage
      \global\@topnum\z@   % Prevents figures from going at top of page.
      \@maketitle
    \fi
    \thispagestyle{plain}\@thanks
  \endgroup
  \setcounter{footnote}{0}%
  \global\let\thanks\relax
  \global\let\maketitle\relax
  \global\let\@maketitle\relax
  \global\let\@thanks\@empty
  \global\let\@author\@empty
  \global\let\@date\@empty
  \global\let\@title\@empty
  \global\let\title\relax
  \global\let\author\relax
  \global\let\date\relax
  \global\let\and\relax
}

\def\@maketitle{%
  \newpage
  \null
  \vskip 2em%
  \begin{center}%
  \let \footnote \thanks
    {\LARGE \@title \par}%
    \vskip 1.5em%
    {\large
      \lineskip .5em%
      \begin{tabular}[t]{c}%
        \@author
      \end{tabular}\par}%
    \vskip 1em%
    {\large \@date}%
  \end{center}%
  \par
  \vskip 1.5em}

% ============================================================================
% Section Formatting
% ============================================================================

\renewcommand\section{\@startsection {section}{1}{\z@}%
                                   {-3.5ex \@plus -1ex \@minus -.2ex}%
                                   {2.3ex \@plus.2ex}%
                                   {\normalfont\Large\bfseries}}

\renewcommand\subsection{\@startsection{subsection}{2}{\z@}%
                                     {-3.25ex\@plus -1ex \@minus -.2ex}%
                                     {1.5ex \@plus .2ex}%
                                     {\normalfont\large\bfseries}}

\renewcommand\subsubsection{\@startsection{subsubsection}{3}{\z@}%
                                     {-3.25ex\@plus -1ex \@minus -.2ex}%
                                     {1.5ex \@plus .2ex}%
                                     {\normalfont\normalsize\bfseries}}

% ============================================================================
% Caption Formatting
% ============================================================================

\usepackage{caption}
\captionsetup{
  font=small,
  labelfont=bf,
  format=hang,
  margin=0.5cm
}

% ============================================================================
% Abstract Formatting
% ============================================================================

\renewcommand\abstract{%
  \if@twocolumn
    \section*{Abstract}%
  \else
    \small
    \begin{center}%
      {\bfseries\abstractname\vspace{-.5em}\vspace{\z@}}%
    \end{center}%
    \quotation
  \fi}

\renewcommand\endabstract{%
  \if@twocolumn\else\endquotation\fi}

% ============================================================================
% Keywords Formatting
% ============================================================================

\newcommand\keywords[1]{%
  \par\addvspace\medskipamount
  {\noindent\small\bfseries Keywords:\,} #1}

% ============================================================================
% Hyperref Configuration
% ============================================================================

\hypersetup{
  colorlinks=true,
  citecolor=blue,
  linkcolor=blue,
  urlcolor=blue,
  breaklinks=true
}

% ============================================================================
% Footnote Formatting
% ============================================================================

\renewcommand\footnoterule{%
  \kern-3\p@
  \hrule\@width.4\columnwidth
  \kern2.6\p@}

\renewcommand\thefootnote{\fnsymbol{footnote}}

% ============================================================================
% References
% ============================================================================

\bibliographystyle{agsm}
\renewcommand\refname{References}

\endinput
